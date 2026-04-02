# ==============================================================================
# TERMINAL QUANTITATIVO NEMESIS - MOTOR PRINCIPAL
# O orquestrador central. Ele puxa os dados, calcula a matemática e toma a decisão.
# ==============================================================================

import time
import os
import msvcrt  # Biblioteca nativa do Windows para capturar teclas sem travar o loop
import MetaTrader5 as mt5
from datetime import datetime

# Importando nossos módulos locais (Todas as ferramentas do nosso canivete suíço)
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
from strategies.analise_pregao import analisar_cenario_avancado
from strategies.microestrutura import cacador_de_absorcao
from core.macro_calendar import verificar_alerta_macro
from core.logger import log

# Ferramentas de Comunicação e Execução
from core.telegram_notifier import notificar_telegram, notificar_execucao
from core.mt5_executor import executar_ordem

# Configurações de Ativos
TICKER_WIN = "WINJ26"
TICKER_VIX = "VIX"
TICKER_DXY = "USDX"
TICKER_SP  = "US500"

# Cores para o Terminal (Deixa a leitura visual mais rápida)
VERDE = '\033[92m'
VERMELHO = '\033[91m'
AMARELO = '\033[93m'
AZUL = '\033[96m'
MAGENTA = '\033[95m'
RESET = '\033[0m'

def limpar_tela():
    """Limpa o prompt de comando para criar o efeito de painel atualizado"""
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    # Inicia a conexão com o banco de dados (nossa caixa-preta)
    conn = inicializar_banco()
    log.info("=== SISTEMA QUANTITATIVO INICIADO ===")
    
    # Memória Anti-Spam para o Telegram
    ultimo_sinal_enviado = ""
    ultimo_alerta_enviado = ""
    tempo_ultimo_sinal = 0  
    COOLDOWN_MINUTOS = 5  # Tempo de silêncio do Telegram entre sinais repetidos

    # Trava de Segurança Mestre do Auto-Trading (Inicia sempre desligado)
    auto_trading_ativo = False
    
    # Loop Infinito (O coração do robô batendo)
    while True:
        limpar_tela()
        hora_atual = datetime.now().strftime("%H:%M:%S")
        print(f"🔄 Executando Motor Quantitativo Modular... [{hora_atual}]")

        # =================================================================
        # 1. EXTRAÇÃO DE DADOS (O Para-brisa)
        # =================================================================
        # Puxamos 600 barras do 5M para garantir a leitura da madrugada (Overnight)
        df_win_full = puxar_dados(TICKER_WIN, CAMINHO_GENIAL, mt5.TIMEFRAME_M5, 600, completo=True)
        df_vix = puxar_dados(TICKER_VIX, CAMINHO_ZERO, mt5.TIMEFRAME_M5, 600)
        df_dxy = puxar_dados(TICKER_DXY, CAMINHO_ZERO, mt5.TIMEFRAME_M5, 600)
        df_sp  = puxar_dados(TICKER_SP, CAMINHO_ZERO, mt5.TIMEFRAME_M5, 600)
        
        # NOVO: Puxa silenciosamente as últimas 15 velas de 1 minuto (M1)
        df_win_m1 = puxar_dados(TICKER_WIN, CAMINHO_GENIAL, mt5.TIMEFRAME_M1, 15, completo=True)
        
        # Puxamos a tendência da maré maior (Gráfico de 1 Hora)
        df_win_60m = puxar_dados(TICKER_WIN, CAMINHO_GENIAL, mt5.TIMEFRAME_H1, 50)
        df_sp_60m  = puxar_dados(TICKER_SP, CAMINHO_ZERO, mt5.TIMEFRAME_H1, 50)

        # Se falhar a internet ou o MT5 cair, ele avisa e tenta de novo sem quebrar
        if any(df is None for df in [df_win_full, df_vix, df_dxy, df_sp, df_win_60m, df_sp_60m, df_win_m1]):
            print(f"{VERMELHO}Erro de conexão MT5. Tentando novamente...{RESET}")
            log.error("Falha de comunicação com MetaTrader 5 (Genial ou Zero Markets).") 
            time.sleep(10) 
            continue

        # =================================================================
        # 2. MOTOR MATEMÁTICO (A Inteligência)
        # =================================================================
        # Calcula VWAP, Volume, e os Z-Scores globais (Termômetro)
        vwap_atual, vol_atual, vol_media = calcular_vwap_e_volume(df_win_full)
        df_win_close = df_win_full[['close']].rename(columns={'close': TICKER_WIN})        
        df_final = calcular_zscore_e_termometro(df_win_close, df_vix, df_dxy, df_sp, TICKER_WIN, TICKER_SP, TICKER_DXY, TICKER_VIX)
        
        # Proteção caso seja início do dia e não tenha dados da madrugada suficientes
        if df_final.empty:
            print(f"{AMARELO}Aguardando sobreposição de fuso horário da madrugada...{RESET}")
            time.sleep(10)
            continue
            
        # Calcula Tendência 60M, ATR (Risco), POC (Volume Acumulado) e Correlação
        tendencia_win = calcular_tendencia_60m(df_win_60m, TICKER_WIN)
        tendencia_sp = calcular_tendencia_60m(df_sp_60m, TICKER_SP)
        atr_atual = calcular_atr(df_win_full)
        poc_atual = calcular_poc_intradiario(df_win_full)
        correlacao_atual = calcular_correlacao_sp(df_win_close, df_sp)

        # Extração das variáveis atuais para tomada de decisão
        linha_atual = df_final.iloc[-1]
        fechamento_candle = linha_atual.name.strftime("%H:%M")
        fechamento_win = df_win_full['close'].iloc[-1]
        distancia_vwap = fechamento_win - vwap_atual
        tem_volume = vol_atual > vol_media
        term_valor = linha_atual['Termometro']
        z_win = linha_atual[f'Z_{TICKER_WIN}']
        timestamp_db = linha_atual.name.strftime("%Y-%m-%d %H:%M:00")

        # Verifica Calendário Econômico (Payroll, FOMC, etc)
        alerta_macro = verificar_alerta_macro(hora_atual)

        # =================================================================
        # 3. ESTRATÉGIA E DECISÃO (O Cérebro)
        # =================================================================
        sinal_txt, sinal_db, mensagem = analisar_cenario_avancado(
            term_valor, tendencia_sp, tendencia_win, fechamento_win, vwap_atual, 
            tem_volume, distancia_vwap, poc_atual, atr_atual, correlacao_atual, alerta_macro
        )

        # -----------------------------------------------------------------
        # NOVO: FILTRO DE WARM-UP INSTITUCIONAL (AMACIAMENTO) E [MICROESTRUTURA]
        # -----------------------------------------------------------------
        agora_dt = datetime.now()
        # Calcula quantos minutos se passaram desde a abertura (09:00)
        minutos_desde_abertura = (agora_dt.hour * 60 + agora_dt.minute) - (9 * 60)
        em_warmup = 0 <= minutos_desde_abertura < 15

        if em_warmup and sinal_db in ["COMPRA", "VENDA"]:
            # Antes de bloquear cega e puramente, consultamos o M1 (A Microestrutura)
            absorveu, msg_microestrutura = cacador_de_absorcao(df_win_m1, sinal_db)
            
            if absorveu:
                # O FURA-FILA: O M1 confirmou a intuição de tela (Craquezinho com Volume)
                log.info(f"FURA-FILA WARM-UP ATIVADO: {msg_microestrutura}")
                mensagem = f"Warm-up ignorado por gatilho de MICROESTRUTURA. {msg_microestrutura}"
                sinal_txt = f"🔥 {sinal_db} (Antecipação Institucional M1)"
                # O sinal_db continua como "COMPRA" ou "VENDA", permitindo que a ordem seja executada!
            else:
                # Se não tem absorção no M1, a regra do escudo prevalece. Bloqueia a tendência.
                sinal_db = f"{sinal_db} BLOQUEADA"
                mensagem = f"Warm-up de Abertura. A VWAP não ancorou. {msg_microestrutura}"
                sinal_txt = f"⚠️ {sinal_db} (Aguardando Amaciamento)"
        # -----------------------------------------------------------------

        # =================================================================
        # 4. GATILHOS DE COMUNICAÇÃO (TELEGRAM) E EXECUÇÃO (AUTO-TRADING)
        # =================================================================
        
        horario_abertura = agora_dt.replace(hour=8, minute=55, second=0, microsecond=0)
        horario_fechamento = agora_dt.replace(hour=18, minute=0, second=0, microsecond=0)
        dentro_do_pregao = horario_abertura <= agora_dt <= horario_fechamento

        # A) Notifica Alerta Macro (Apenas 1 vez por evento)
        if alerta_macro and alerta_macro != ultimo_alerta_enviado and dentro_do_pregao:
            notificar_telegram("ALERTA MACRO", sinal_db, alerta_macro, fechamento_win, term_valor, distancia_vwap, tem_volume, tendencia_win, atr_atual, poc_atual)
            ultimo_alerta_enviado = alerta_macro
        if not alerta_macro:
            ultimo_alerta_enviado = ""

        # B) Gatilho de Sinais Inteligente (A Máquina de Estados Anti-Spam)
        # Adicionamos TODAS as strings de bloqueio aqui para o robô silenciá-las
        sinais_alerta = ["COMPRA", "VENDA", "DESCOLAMENTO_MACRO", "BLOQUEIO_ELASTICO", "COMPRA BLOQUEADA", "VENDA BLOQUEADA", "OPERAÇÃO BLOQUEADA"]
        sinais_operacionais = ["COMPRA", "VENDA"] 
        agora = time.time()
        
        if sinal_db in sinais_alerta and dentro_do_pregao:
            mudou_status = (sinal_db != ultimo_sinal_enviado)
            passou_cooldown = (agora - tempo_ultimo_sinal) > (COOLDOWN_MINUTOS * 60)
            
            # Só avisa se for um Status NOVO ou se for um Sinal Operacional cujo Cooldown já expirou.
            deve_notificar = mudou_status or (sinal_db in sinais_operacionais and passou_cooldown)
            
            if deve_notificar:
                # 1. Avisa o Operador no Telegram
                notificar_telegram("SINAL", sinal_db, mensagem, fechamento_win, term_valor, distancia_vwap, tem_volume, tendencia_win, atr_atual, poc_atual)
                ultimo_sinal_enviado = sinal_db
                tempo_ultimo_sinal = agora

                # 2. EXECUÇÃO AUTOMÁTICA (Apenas se for Compra/Venda limpa)
                if auto_trading_ativo and sinal_db in sinais_operacionais:
                    posicoes_abertas = mt5.positions_get(magic=777)
                    if posicoes_abertas is None or len(posicoes_abertas) == 0:
                        log.info(f"Auto-Trading acionado. Iniciando protocolo de {sinal_db}.")
                        
                        stop_pts = atr_atual
                        alvo_pts = atr_atual * 1.5
                        lote_operacional = 1.0 
                        
                        resultado_ordem = executar_ordem(TICKER_WIN, sinal_db, lote_operacional, fechamento_win, stop_pts, alvo_pts)
                        
                        if resultado_ordem:
                            notificar_execucao(
                                acao=sinal_db, 
                                simbolo=TICKER_WIN, 
                                preco=resultado_ordem['preco_executado'], 
                                lote=resultado_ordem['lote'], 
                                sl=resultado_ordem['sl'], 
                                tp=resultado_ordem['tp'],
                                motivo="Fluxo Confirmado + ATR"
                            )
                    else:
                        log.info("Sinal ignorado pelo Auto-Trading: Já existe uma posição aberta.")

        # Salva auditoria na Caixa Preta (Logs e Banco de Dados)
        log.info(f"WIN: {fechamento_win:.0f} | Termômetro: {term_valor:.2f} | Decisão: {sinal_db}")
        dados_bd = (
            timestamp_db, fechamento_win, z_win, linha_atual[f'Z_{TICKER_SP}'], 
            linha_atual[f'Z_{TICKER_DXY}'], linha_atual[f'Z_{TICKER_VIX}'], 
            term_valor, sinal_db, vwap_atual, distancia_vwap, vol_atual, vol_media
        )
        salvar_leitura(conn, dados_bd)

        # =================================================================
        # 5. RENDERIZAÇÃO DA TELA (Painel Visual)
        # =================================================================
        cor_vol = VERDE if tem_volume else AMARELO
        status_vol_txt = "ACIMA da Média (Confirmado)" if tem_volume else "ABAIXO da Média (Movimento Oco)"
        status_vwap = f"{VERDE}Preço Acima (Comprados no Controle){RESET}" if distancia_vwap > 0 else f"{VERMELHO}Preço Abaixo (Vendidos no Controle){RESET}"
        cor_win_60 = VERDE if tendencia_win == "ALTA" else VERMELHO
        cor_sp_60 = VERDE if tendencia_sp == "ALTA" else VERMELHO

        limpar_tela()
        print("="*65)
        print(f"   TERMÔMETRO INSTITUCIONAL - MACRO + VWAP + 60M + VOLUME   ")
        print("="*65)
        print(f"Última Atualização: {hora_atual} | Ref. Candle: {fechamento_candle}\n")
        
        print(f"► SINAL ATUAL: {sinal_txt}\n")
        print(f"Pontuação Termômetro Global: {term_valor:.2f}")
        print("-" * 65)
        
        print(f"📊 FLUXO DE VOLUME (No Candle de 5M Atual):")
        print(f"   Status do Lote: {cor_vol}{status_vol_txt}{RESET}")
        print(f"   Vol. Atual: {vol_atual:.0f} | Vol. Médio: {vol_media:.0f}")
        print("-" * 65)

        print(f"🧲 GRAVIDADE INSTITUCIONAL (VWAP Diária):")
        print(f"   VWAP Atual   : {vwap_atual:.0f}")
        print(f"   Distância    : {distancia_vwap:+.0f} pontos -> {status_vwap}")
        print("-" * 65)

        print(f"🎯 POC Atual: {poc_atual:.0f} | 📏 ATR (Volatilidade): {atr_atual:.0f} pts | 🔗 Corr(WINxSP): {correlacao_atual:.2f}")

        print(f"🌊 FILTRO MACRO (Tendência 60 Minutos):")
        print(f"   Maré Local (WIN)  : {cor_win_60}{tendencia_win}{RESET}")
        print(f"   Maré Global (S&P) : {cor_sp_60}{tendencia_sp}{RESET}")
        print("-" * 65)
        
        print(f"{AZUL}💡 ANÁLISE DO CENÁRIO:{RESET}")
        print(f"   {mensagem}")
        print("="*65)
        
        print("RAIO-X DOS ATIVOS (Z-Score no 5M):")
        print(f"🇧🇷 WIN  : {z_win:>5.2f} (Cot: {fechamento_win:.0f})")
        print(f"🇺🇸 S&P  : {linha_atual[f'Z_{TICKER_SP}']:>5.2f}")
        print(f"💵 DXY  : {linha_atual[f'Z_{TICKER_DXY}']:>5.2f}")
        print(f"😨 VIX  : {linha_atual[f'Z_{TICKER_VIX}']:>5.2f}")
        print("="*65)
                
        # Painel de Status do Auto-Trading
        status_cor = VERDE if auto_trading_ativo else VERMELHO
        status_texto = "LIGADO" if auto_trading_ativo else "DESLIGADO"
        print("="*75)
        print(f"🤖 AUTO-TRADING: {status_cor}{status_texto}{RESET} (Pressione 'A' para alternar)")
        print("="*75)
        
        print("Aguardando 10 segundos... (Teclas: 'T' = Telegram | 'A' = Ligar/Desl Auto-Trading)")

        # =================================================================
        # 6. ESPERA INTELIGENTE E CAPTURA DE TECLAS (Non-Blocking)
        # =================================================================
        espera_segundos = 10
        tempo_inicial = time.time()
        
        # O programa fica preso neste micro-loop por 10 segundos prestando atenção no teclado
        while time.time() - tempo_inicial < espera_segundos:
            # Se o usuário apertar fisicamente alguma tecla
            if msvcrt.kbhit():
                tecla = msvcrt.getch().decode('utf-8', errors='ignore').lower()
                
                # Tecla T: Dispara mensagem manual pro Telegram
                if tecla == 't':
                    print(f"\n{MAGENTA}🚀 [HOTKEY] Tecla 'T' acionada! Disparando envio manual...{RESET}")
                    notificar_telegram("VALIDAÇÃO MANUAL", sinal_db, mensagem, fechamento_win, term_valor, distancia_vwap, tem_volume, tendencia_win, atr_atual, poc_atual)
                    while msvcrt.kbhit(): msvcrt.getch() # Limpa o buffer de teclas (Evita duplo clique)
                    time.sleep(1) 
                    
                # Tecla A: Liga ou Desliga o Robô de Execução
                elif tecla == 'a':
                    auto_trading_ativo = not auto_trading_ativo
                    estado_log = "ATIVADO" if auto_trading_ativo else "DESATIVADO"
                    log.info(f"Comando manual: Auto-Trading {estado_log} pelo usuário.")
                    while msvcrt.kbhit(): msvcrt.getch() # Limpa buffer
                    break # Quebra o loop de espera para atualizar a tela imediatamente e mostrar a cor vermelha/verde
            
            time.sleep(0.1) # Dorme 100ms a cada ciclo para não sobrecarregar a CPU

if __name__ == "__main__":
    main()