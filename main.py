# ==============================================================================
# TERMINAL QUANTITATIVO NEMESIS - MOTOR PRINCIPAL
# ==============================================================================

import time
import os
import asyncio
import msvcrt
import MetaTrader5 as mt5
from datetime import datetime
from typing import Optional

from core.database import inicializar_banco, salvar_leitura
from core.mt5_feed import puxar_dados, CAMINHO_GENIAL, CAMINHO_ZERO
from core.math_engine import (
    calcular_vwap_e_volume, 
    calcular_zscore_e_termometro, 
    calcular_tendencia_60m, 
    calcular_atr, 
    calcular_poc_intradiario, 
    calcular_correlacao_sp
)
from core.models import MarketContext, AnalysisResult, FlowAnalysisResult, SequentialValidationResult
from strategies.analise_pregao import analisar_cenario_avancado
from strategies.microestrutura import analisar_fluxo_m1, confirmar_sequencial
from core.macro_calendar import verificar_alerta_macro
from core.logger import log
from core.config import cfg

from core.telegram_notifier import notificar_telegram, notificar_execucao
from core.mt5_executor import executar_ordem, zerar_posicoes
from core.trade_manager import gerenciar_trailing_stop

TICKER_WIN = cfg.TICKER_WIN
TICKER_VIX = cfg.TICKER_VIX
TICKER_DXY = cfg.TICKER_DXY
TICKER_SP  = cfg.TICKER_SP

VERDE = '\033[92m'
VERMELHO = '\033[91m'
AMARELO = '\033[93m'
AZUL = '\033[96m'
MAGENTA = '\033[95m'
RESET = '\033[0m'

def limpar_tela() -> None:
    os.system('cls' if os.name == 'nt' else 'clear')


class TradingOrchestrator:
    def __init__(self):
        self.conn = inicializar_banco()
        self.ultimo_sinal_enviado = ""
        self.ultimo_alerta_enviado = ""
        self.tempo_ultimo_sinal = 0  
        self.cooldown_minutos = 5
        self.auto_trading_ativo = False
        
        # Parâmetros de risco e gestão
        self.lote_piloto = 1.0
        self.lote_maximo = 3.0
        self.flag_tecla_t = False
        
        log.info("=== SISTEMA QUANTITATIVO INICIADO ===")
        
    def extrair_dados(self) -> Optional[tuple]:
        """1. EXTRAÇÃO DE DADOS BATCH"""
        # Batch Genial
        if not mt5.initialize(path=CAMINHO_GENIAL):
            return None
        df_win_full = puxar_dados(TICKER_WIN, CAMINHO_GENIAL, mt5.TIMEFRAME_M5, 600, completo=True, skip_init_shutdown=True)
        df_win_m1 = puxar_dados(TICKER_WIN, CAMINHO_GENIAL, mt5.TIMEFRAME_M1, 15, completo=True, skip_init_shutdown=True)
        df_win_60m = puxar_dados(TICKER_WIN, CAMINHO_GENIAL, mt5.TIMEFRAME_H1, 50, skip_init_shutdown=True)
        mt5.shutdown()

        # Batch Zero Markets
        if not mt5.initialize(path=CAMINHO_ZERO):
            return None
        df_vix = puxar_dados(TICKER_VIX, CAMINHO_ZERO, mt5.TIMEFRAME_M5, 600, skip_init_shutdown=True)
        df_dxy = puxar_dados(TICKER_DXY, CAMINHO_ZERO, mt5.TIMEFRAME_M5, 600, skip_init_shutdown=True)
        df_sp  = puxar_dados(TICKER_SP, CAMINHO_ZERO, mt5.TIMEFRAME_M5, 600, skip_init_shutdown=True)
        df_sp_60m  = puxar_dados(TICKER_SP, CAMINHO_ZERO, mt5.TIMEFRAME_H1, 50, skip_init_shutdown=True)
        mt5.shutdown()

        # Reconecta e mantém Aberto no terminal Genial para a engine realizar o envio de Ordens 
        mt5.initialize(path=CAMINHO_GENIAL)
        
        if any(df is None for df in [df_win_full, df_vix, df_dxy, df_sp, df_win_60m, df_sp_60m, df_win_m1]):
            return None
            
        return (df_win_full, df_vix, df_dxy, df_sp, df_win_m1, df_win_60m, df_sp_60m)

    def processar_motor_matematico(self, dfs: tuple) -> Optional[dict]:
        """2. MOTOR MATEMÁTICO (A Inteligência)"""
        df_win_full, df_vix, df_dxy, df_sp, df_win_m1, df_win_60m, df_sp_60m = dfs
        
        vwap_atual, vol_atual, vol_media = calcular_vwap_e_volume(df_win_full)
        df_win_close = df_win_full[['close']].rename(columns={'close': TICKER_WIN})        
        df_final = calcular_zscore_e_termometro(df_win_close, df_vix, df_dxy, df_sp, TICKER_WIN, TICKER_SP, TICKER_DXY, TICKER_VIX)
        
        if df_final.empty:
            return None

        tendencia_win = calcular_tendencia_60m(df_win_60m, TICKER_WIN)
        tendencia_sp = calcular_tendencia_60m(df_sp_60m, TICKER_SP)
        atr_atual = calcular_atr(df_win_full)
        poc_atual = calcular_poc_intradiario(df_win_full)
        correlacao_atual = calcular_correlacao_sp(df_win_close, df_sp)

        linha_atual = df_final.iloc[-1]
        fechamento_win = float(df_win_full['close'].iloc[-1])
        vol_atual = float(vol_atual)
        vol_media = float(vol_media)
        
        ctx = MarketContext(
            termometro=linha_atual['Termometro'],
            tendencia_sp=tendencia_sp,
            tendencia_win=tendencia_win,
            fechamento_win=fechamento_win,
            vwap_atual=vwap_atual,
            tem_volume=(vol_atual > vol_media),
            distancia_vwap=fechamento_win - vwap_atual,
            poc_atual=poc_atual,
            atr_atual=atr_atual,
            correlacao=correlacao_atual,
            alerta_macro=verificar_alerta_macro(datetime.now().strftime("%H:%M:%S"))
        )
        
        return {
            "ctx": ctx,
            "df_win_m1": df_win_m1,
            "linha_atual": linha_atual,
            "vol_atual": vol_atual,
            "vol_media": vol_media,
            "z_win": linha_atual[f'Z_{TICKER_WIN}'],
        }

    def gerenciar_ordens(self, sinal_db: str, ctx: MarketContext, msg_microestrutura: str):
        """Gerencia execução scale-in de ordens. Refatorado com Guard Clauses."""
        if not self.auto_trading_ativo:
            return
            
        if sinal_db not in ["COMPRA", "VENDA"]:
            return
            
        posicoes_abertas = mt5.positions_get(symbol=TICKER_WIN)
        
        # CENA 1: ESTAMOS ZERADOS (Disparo da Sonda de Reconhecimento)
        if posicoes_abertas is None or len(posicoes_abertas) == 0:
            log.info(f"Auto-Trading acionado. Iniciando Sonda de {sinal_db} ({self.lote_piloto} lote).")
            resultado = executar_ordem(
                TICKER_WIN, sinal_db, self.lote_piloto, ctx.fechamento_win, ctx.atr_atual, ctx.atr_atual * 2.0
            )
            if resultado:
                notificar_execucao(sinal_db, TICKER_WIN, resultado.preco_executado, self.lote_piloto, resultado.sl, resultado.tp, f"Sonda de Absorção: {msg_microestrutura}")
            return

        # CENA 2: JÁ TEMOS POSIÇÃO ABERTA (Análise para Scale-In)
        pos = posicoes_abertas[0]
        direcao_atual = "COMPRA" if pos.type == mt5.ORDER_TYPE_BUY else "VENDA"
        
        if pos.volume >= self.lote_maximo:
            log.info(f"Operação rolando com Mão Cheia ({pos.volume} lotes). Gestor de Trailing Stop assumiu o controle.")
            return
            
        if pos.volume != self.lote_piloto or direcao_atual != sinal_db:
            if direcao_atual != sinal_db:
                log.info(f"Sinal de {sinal_db} ignorado pois estamos posicionados em {direcao_atual}.")
            return
            
        resultado_seq = confirmar_sequencial(TICKER_WIN, direcao_atual)
        if not resultado_seq.confirmado:
            log.info(f"Posição já aberta com Sonda. Aguardando confirmação HFT para adição... {resultado_seq.mensagem}")
            return
            
        log.warning(f"🔥 FLUXO DETECTADO! Acionando Scale-In para encher a mão. {resultado_seq.mensagem}")
        lote_adicional = self.lote_maximo - self.lote_piloto
        resultado_adicao = executar_ordem(
            TICKER_WIN, direcao_atual, lote_adicional, ctx.fechamento_win, ctx.atr_atual, ctx.atr_atual * 1.5
        )
        if resultado_adicao:
            msg_telegram = f"Scale-In Executado! Mão cheia com {self.lote_maximo} lotes. Motivo: {resultado_seq.mensagem}"
            notificar_execucao("ADIÇÃO DE POSIÇÃO", TICKER_WIN, resultado_adicao.preco_executado, lote_adicional, resultado_adicao.sl, resultado_adicao.tp, msg_telegram)

    def rotina_seguranca_liquidacao(self, agora_dt: datetime, dentro_do_pregao: bool, analise: dict):
        horario_zeragem = agora_dt.replace(hour=16, minute=55, second=0, microsecond=0)
        if agora_dt >= horario_zeragem and dentro_do_pregao and self.auto_trading_ativo:
            posicoes = mt5.positions_get(symbol=TICKER_WIN)
            if posicoes and len(posicoes) > 0:
                msg_alerta = "⏰ 16:55 - Acionando Protocolo de Zeragem Forçada para proteger o capital de Gaps noturnos."
                log.warning(msg_alerta)
                ctx = analise["ctx"]
                notificar_telegram("ALERTA CRÍTICO", "ZERAGEM COMPULSÓRIA", msg_alerta, 
                    ctx.fechamento_win, ctx.termometro, ctx.distancia_vwap, 
                    ctx.tem_volume, ctx.tendencia_win, ctx.atr_atual, ctx.poc_atual)
                
                zerar_posicoes(TICKER_WIN)
                self.auto_trading_ativo = False
                log.info("Auto-Trading DESLIGADO automaticamente após a zeragem.")

    def renderizar_tela(self, hora_atual: str, estado: dict, sinal_txt: str, mensagem: str):
        ctx = estado["ctx"]
        cor_vol = VERDE if ctx.tem_volume else AMARELO
        status_vol_txt = "ACIMA da Média (Confirmado)" if ctx.tem_volume else "ABAIXO da Média (Movimento Oco)"
        status_vwap = f"{VERDE}Preço Acima (Comprados no Controle){RESET}" if ctx.distancia_vwap > 0 else f"{VERMELHO}Preço Abaixo (Vendidos no Controle){RESET}"
        cor_win_60 = VERDE if ctx.tendencia_win == "ALTA" else VERMELHO
        cor_sp_60 = VERDE if ctx.tendencia_sp == "ALTA" else VERMELHO

        limpar_tela()
        print("="*65)
        print(f"   TERMÔMETRO INSTITUCIONAL - MACRO + VWAP + 60M + VOLUME   ")
        print("="*65)
        print(f"Última Atualização: {hora_atual} | Ref. Candle: {estado['linha_atual'].name.strftime('%H:%M')}\n")
        
        print(f"► SINAL ATUAL: {sinal_txt}\n")
        print(f"Pontuação Termômetro Global: {ctx.termometro:.2f}")
        print("-" * 65)
        
        print(f"📊 FLUXO DE VOLUME (No Candle de 5M Atual):")
        print(f"   Status do Lote: {cor_vol}{status_vol_txt}{RESET}")
        print(f"   Vol. Atual: {estado['vol_atual']:.0f} | Vol. Médio: {estado['vol_media']:.0f}")
        print("-" * 65)

        print(f"🧲 GRAVIDADE INSTITUCIONAL (VWAP Diária):")
        print(f"   VWAP Atual   : {ctx.vwap_atual:.0f}")
        print(f"   Distância    : {ctx.distancia_vwap:+.0f} pontos -> {status_vwap}")
        print("-" * 65)

        print(f"🎯 POC Atual: {ctx.poc_atual:.0f} | 📏 ATR (Volatilidade): {ctx.atr_atual:.0f} pts | 🔗 Corr(WINxSP): {ctx.correlacao:.2f}")

        print(f"🌊 FILTRO MACRO (Tendência 60 Minutos):")
        print(f"   Maré Local (WIN)  : {cor_win_60}{ctx.tendencia_win}{RESET}")
        print(f"   Maré Global (S&P) : {cor_sp_60}{ctx.tendencia_sp}{RESET}")
        print("-" * 65)
        
        print(f"{AZUL}💡 ANÁLISE DO CENÁRIO:{RESET}")
        print(f"   {mensagem}")
        print("="*65)
        
        print("RAIO-X DOS ATIVOS (Z-Score no 5M):")
        print(f"🇧🇷 WIN  : {estado['z_win']:>5.2f} (Cot: {ctx.fechamento_win:.0f})")
        print(f"🇺🇸 S&P  : {estado['linha_atual'][f'Z_{TICKER_SP}']:>5.2f}")
        print(f"💵 DXY  : {estado['linha_atual'][f'Z_{TICKER_DXY}']:>5.2f}")
        print(f"😨 VIX  : {estado['linha_atual'][f'Z_{TICKER_VIX}']:>5.2f}")
        print("="*65)
                
        status_cor = VERDE if self.auto_trading_ativo else VERMELHO
        status_texto = "LIGADO" if self.auto_trading_ativo else "DESLIGADO"
        print("="*75)
        print(f"🤖 AUTO-TRADING: {status_cor}{status_texto}{RESET} (Pressione 'A' para alternar)")
        print("="*75)
        print("Aguardando 10 segundos... (Teclas: 'T' = Telegram | 'A' = Ligar/Desl Auto-Trading)")

    async def escutar_teclado(self):
        """Task rodando em background para capturar inputs de teclado de forma assíncrona"""
        while True:
            if msvcrt.kbhit():
                tecla = msvcrt.getch().decode('utf-8', errors='ignore').lower()
                
                if tecla == 't':
                    self.flag_tecla_t = True
                elif tecla == 'a':
                    self.auto_trading_ativo = not self.auto_trading_ativo
                    estado_log = "ATIVADO" if self.auto_trading_ativo else "DESATIVADO"
                    log.info(f"Comando manual: Auto-Trading {estado_log} pelo usuário.")
                
                while msvcrt.kbhit(): msvcrt.getch()
            
            await asyncio.sleep(0.1)

    async def aguardar_inteligente(self, analise: dict, sinal_db: str, mensagem: str):
        espera_segundos = 10
        ctx = analise["ctx"]
        
        for _ in range(int(espera_segundos / 0.1)):
            if self.flag_tecla_t:
                print(f"\n{MAGENTA}🚀 [HOTKEY] Tecla 'T' acionada! Disparando envio manual...{RESET}")
                notificar_telegram("VALIDAÇÃO MANUAL", sinal_db, mensagem, 
                    ctx.fechamento_win, ctx.termometro, ctx.distancia_vwap, 
                    ctx.tem_volume, ctx.tendencia_win, ctx.atr_atual, ctx.poc_atual)
                self.flag_tecla_t = False
                await asyncio.sleep(1)
            
            await asyncio.sleep(0.1)

    async def run(self):
        """Loop principal abstraído em orquestrador e assíncrono"""
        task_teclado = asyncio.create_task(self.escutar_teclado())
        try:
            while True:
                limpar_tela()
                agora_dt = datetime.now()
                hora_atual = agora_dt.strftime("%H:%M:%S")
                print(f"🔄 Executando Motor Quantitativo Modular... [{hora_atual}]")

                # 1. Extração de Dados
                dfs = self.extrair_dados()
                if not dfs:
                    print(f"{VERMELHO}Erro de conexão MT5. Tentando novamente...{RESET}")
                    log.error("Falha de comunicação com MetaTrader 5 (Genial ou Zero Markets).") 
                    await asyncio.sleep(10) 
                    continue

                # 2. Processamento Matemático
                estado = self.processar_motor_matematico(dfs)
                if not estado:
                    print(f"{AMARELO}Aguardando sobreposição de fuso horário da madrugada...{RESET}")
                    await asyncio.sleep(10)
                    continue

                ctx: MarketContext = estado["ctx"]
                df_win_m1 = estado["df_win_m1"]
                
                # 3. Estratégia e Decisão
                resultado_analise: AnalysisResult = analisar_cenario_avancado(ctx)
                sinal_db = resultado_analise.sinal_db
                sinal_txt = resultado_analise.sinal_txt
                mensagem = resultado_analise.mensagem

                # Filtros de Horário e Fluxo
                minutos_desde_abertura = (agora_dt.hour * 60 + agora_dt.minute) - (9 * 60)
                em_warmup = 0 <= minutos_desde_abertura < 15
                horario_corte = agora_dt.replace(hour=16, minute=45, second=0, microsecond=0)
                pode_abrir_ordem = agora_dt <= horario_corte

                msg_microestrutura = ""
                if sinal_db in ["COMPRA", "VENDA"]:
                    if not pode_abrir_ordem:
                        sinal_db = f"{sinal_db} BLOQUEADA"
                        mensagem = f"Horário limite atingido ({horario_corte.strftime('%H:%M')}). Novas operações bloqueadas."
                        sinal_txt = f"⏳ {sinal_db} (Fim de Expediente)"
                    else:
                        fluxo_result: FlowAnalysisResult = analisar_fluxo_m1(TICKER_WIN, df_win_m1, sinal_db)
                        fluxo_aprovado = fluxo_result.aprovado
                        msg_microestrutura = fluxo_result.mensagem

                        if em_warmup:
                            if fluxo_aprovado and "FURA-FILA" in msg_microestrutura:
                                log.info(f"FURA-FILA WARM-UP ATIVADO: {msg_microestrutura}")
                                mensagem = f"Warm-up ignorado por gatilho de MICROESTRUTURA. {msg_microestrutura}"
                                sinal_txt = f"🔥 {sinal_db} (Antecipação Institucional M1)"
                            else:
                                sinal_db = f"{sinal_db} BLOQUEADA"
                                mensagem = f"Warm-up de Abertura. A VWAP não ancorou. {msg_microestrutura}"
                                sinal_txt = f"⚠️ {sinal_db} (Aguardando Amaciamento)"
                        else:
                            if not fluxo_aprovado and "BLOQUEIO" in msg_microestrutura:
                                sinal_db = f"{sinal_db} BLOQUEADA"
                                mensagem = f"Falso Rompimento Detectado pela Fita! {msg_microestrutura}"
                                sinal_txt = f"🛑 {sinal_db} (Sem Saldo Delta)"
                                log.warning(mensagem)
                            elif fluxo_aprovado and "FURA-FILA" in msg_microestrutura:
                                mensagem += f" | Crivo do Fluxo: {msg_microestrutura}"
                                sinal_txt = f"🎯 {sinal_db} (Confirmação M1)"

                horario_abertura = agora_dt.replace(hour=8, minute=55, second=0, microsecond=0)
                horario_fechamento = agora_dt.replace(hour=18, minute=0, second=0, microsecond=0)
                dentro_do_pregao = horario_abertura <= agora_dt <= horario_fechamento

                # 4. Gatilhos de Comunicação e Segurança
                self.rotina_seguranca_liquidacao(agora_dt, dentro_do_pregao, estado)

                if ctx.alerta_macro and ctx.alerta_macro != self.ultimo_alerta_enviado and dentro_do_pregao:
                    notificar_telegram("ALERTA MACRO", sinal_db, ctx.alerta_macro, ctx.fechamento_win, ctx.termometro, ctx.distancia_vwap, ctx.tem_volume, ctx.tendencia_win, ctx.atr_atual, ctx.poc_atual)
                    self.ultimo_alerta_enviado = ctx.alerta_macro
                if not ctx.alerta_macro:
                    self.ultimo_alerta_enviado = ""

                sinais_alerta = ["COMPRA", "VENDA", "DESCOLAMENTO_MACRO", "BLOQUEIO_ELASTICO", "COMPRA BLOQUEADA", "VENDA BLOQUEADA", "OPERAÇÃO BLOQUEADA"]
                sinais_operacionais = ["COMPRA", "VENDA"] 
                agora = time.time()
                
                if sinal_db in sinais_alerta and dentro_do_pregao:
                    mudou_status = (sinal_db != self.ultimo_sinal_enviado)
                    passou_cooldown = (agora - self.tempo_ultimo_sinal) > (self.cooldown_minutos * 60)
                    deve_notificar = mudou_status or (sinal_db in sinais_operacionais and passou_cooldown)
                    
                    if deve_notificar:
                        notificar_telegram("SINAL", sinal_txt, mensagem, ctx.fechamento_win, ctx.termometro, ctx.distancia_vwap, ctx.tem_volume, ctx.tendencia_win, ctx.atr_atual, ctx.poc_atual)
                        self.ultimo_sinal_enviado = sinal_db
                        self.tempo_ultimo_sinal = agora

                        if pode_abrir_ordem:
                            self.gerenciar_ordens(sinal_db, ctx, msg_microestrutura)

                # Salva auditoria no Banco de Dados
                timestamp_db = estado["linha_atual"].name.strftime("%Y-%m-%d %H:%M:00")
                log.info(f"WIN: {ctx.fechamento_win:.0f} | Termômetro: {ctx.termometro:.2f} | Decisão: {sinal_db}")
                dados_bd = (
                    timestamp_db, ctx.fechamento_win, estado["z_win"], estado["linha_atual"][f'Z_{TICKER_SP}'], 
                    estado["linha_atual"][f'Z_{TICKER_DXY}'], estado["linha_atual"][f'Z_{TICKER_VIX}'], 
                    ctx.termometro, sinal_db, ctx.vwap_atual, ctx.distancia_vwap, estado["vol_atual"], estado["vol_media"]
                )
                salvar_leitura(self.conn, dados_bd)

                # 5. Renderização (Painel)
                self.renderizar_tela(hora_atual, estado, sinal_txt, mensagem)

                # 6. Gestão Ativa
                if self.auto_trading_ativo and dentro_do_pregao:
                    gerenciar_trailing_stop(TICKER_WIN, gatilho_pts=250, margem_seguranca=100, trailing_step=30)

                # 7. Espera Inteligente
                await self.aguardar_inteligente(estado, sinal_db, mensagem)
        except asyncio.CancelledError:
            pass
        finally:
            task_teclado.cancel()


if __name__ == "__main__":
    orquestrador = TradingOrchestrator()
    try:
        asyncio.run(orquestrador.run())
    except KeyboardInterrupt:
        log.info("Encerrando bot manualmente.")
        print("\nSaindo...")