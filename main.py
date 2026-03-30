# O maestro que junta tudo e roda o painel
# O orquestrador. Ficou limpo, minúsculo e elegante. Ele só chama os módulos.

import time
import os
import msvcrt  # Biblioteca nativa do Windows para capturar teclas
import MetaTrader5 as mt5
from datetime import datetime

# Importando nossos módulos locais
from core.database import inicializar_banco, salvar_leitura
from core.mt5_feed import puxar_dados, CAMINHO_GENIAL, CAMINHO_ZERO
from core.math_engine import calcular_vwap_e_volume, calcular_zscore_e_termometro, calcular_tendencia_60m
from strategies.analise_pregao import analisar_cenario_avancado
from core.math_engine import calcular_atr, calcular_poc_intradiario, calcular_correlacao_sp
from core.macro_calendar import verificar_alerta_macro
from core.logger import log

# Configurações
TICKER_WIN = "WINJ26"
TICKER_VIX = "VIX"
TICKER_DXY = "USDX"
TICKER_SP  = "US500"

# Cores para o Terminal
VERDE = '\033[92m'
VERMELHO = '\033[91m'
AMARELO = '\033[93m'
AZUL = '\033[96m'
MAGENTA = '\033[95m'
RESET = '\033[0m'

def limpar_tela():
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    conn = inicializar_banco()
    
    log.info("=== SISTEMA QUANTITATIVO INICIADO ===")
    
    # Memória Anti-Spam para o Telegram
    ultimo_sinal_enviado = ""
    ultimo_alerta_enviado = ""
    tempo_ultimo_sinal = 0  # NOVO: Cronômetro do sinal
    # Se quiser que o Telegram fique mais "tagarela", é só mudar o COOLDOWN_MINUTOS = 5 para 3. Se quiser mais silêncio, mude para 10!
    COOLDOWN_MINUTOS = 5    # NOVO: Tempo de silêncio (ajuste como quiser).
    
    while True:
        limpar_tela()
        hora_atual = datetime.now().strftime("%H:%M:%S")
        print(f"🔄 Executando Motor Quantitativo Modular... [{hora_atual}]")

        # 1. Extração de Dados (core/mt5_feed.py)
        # Puxamos 600 barras para garantir o "overlap" entre a B3 de ontem e o Global de hoje
        df_win_full = puxar_dados(TICKER_WIN, CAMINHO_GENIAL, mt5.TIMEFRAME_M5, 600, completo=True)
        df_vix = puxar_dados(TICKER_VIX, CAMINHO_ZERO, mt5.TIMEFRAME_M5, 600)
        df_dxy = puxar_dados(TICKER_DXY, CAMINHO_ZERO, mt5.TIMEFRAME_M5, 600)
        df_sp  = puxar_dados(TICKER_SP, CAMINHO_ZERO, mt5.TIMEFRAME_M5, 600)
        
        df_win_60m = puxar_dados(TICKER_WIN, CAMINHO_GENIAL, mt5.TIMEFRAME_H1, 50)
        df_sp_60m  = puxar_dados(TICKER_SP, CAMINHO_ZERO, mt5.TIMEFRAME_H1, 50)

        if any(df is None for df in [df_win_full, df_vix, df_dxy, df_sp, df_win_60m, df_sp_60m]):
            mensagem_erro = "Erro de conexão MT5. Tentando novamente em 10s..."
            print(f"{VERMELHO}Erro de conexão MT5. Tentando novamente...{RESET}")
            log.error("Falha de comunicação com MetaTrader 5 (Genial ou Zero Markets).") # LOG DE ERRO
            time.sleep(10) 
            continue

        # 2. Motor Matemático Evoluído (core/math_engine.py)
        vwap_atual, vol_atual, vol_media = calcular_vwap_e_volume(df_win_full)
        df_win_close = df_win_full[['close']].rename(columns={'close': TICKER_WIN})        
        df_final = calcular_zscore_e_termometro(df_win_close, df_vix, df_dxy, df_sp, TICKER_WIN, TICKER_SP, TICKER_DXY, TICKER_VIX)
        
        if df_final.empty:
            print(f"{AMARELO}Aguardando sobreposição de fuso horário da madrugada...{RESET}")
            time.sleep(10)
            continue
            
        tendencia_win = calcular_tendencia_60m(df_win_60m, TICKER_WIN)
        tendencia_sp = calcular_tendencia_60m(df_sp_60m, TICKER_SP)
        
        # Novas Métricas Bloomberg
        atr_atual = calcular_atr(df_win_full)
        poc_atual = calcular_poc_intradiario(df_win_full)
        correlacao_atual = calcular_correlacao_sp(df_win_close, df_sp)

        # Extração das variáveis atuais
        linha_atual = df_final.iloc[-1]
        fechamento_candle = linha_atual.name.strftime("%H:%M")
        fechamento_win = df_win_full['close'].iloc[-1]
        distancia_vwap = fechamento_win - vwap_atual
        tem_volume = vol_atual > vol_media
        term_valor = linha_atual['Termometro']
        z_win = linha_atual[f'Z_{TICKER_WIN}']
        timestamp_db = linha_atual.name.strftime("%Y-%m-%d %H:%M:00")

        # Verifica se tem alguma bomba macroeconômica prestes a explodir
        alerta_macro = verificar_alerta_macro(hora_atual)

        # 3. Estratégia e Decisão (Evoluída com Calendário)
        sinal_txt, sinal_db, mensagem = analisar_cenario_avancado(
            term_valor, tendencia_sp, tendencia_win, fechamento_win, vwap_atual, 
            tem_volume, distancia_vwap, poc_atual, atr_atual, correlacao_atual, alerta_macro
        )

        # --- GATILHO DO TELEGRAM (ANTI-SPAM) ---
        from core.telegram_notifier import notificar_telegram
        
        # 1. Notifica Alerta Macro (Apenas 1 vez por evento)
        if alerta_macro and alerta_macro != ultimo_alerta_enviado:
            notificar_telegram("ALERTA MACRO", sinal_db, alerta_macro, fechamento_win, term_valor, distancia_vwap, tem_volume, tendencia_win, atr_atual, poc_atual)
            ultimo_alerta_enviado = alerta_macro
            
        if not alerta_macro:
            ultimo_alerta_enviado = ""

        # 2. Notifica Sinais Fortes Institucionais com Cooldown
        sinais_alerta = ["COMPRA", "VENDA", "DESCOLAMENTO_MACRO"]
        agora = time.time()
        
        if sinal_db in sinais_alerta:
            # Dispara se for um sinal INÉDITO/DIFERENTE, OU se já passou o tempo de silêncio
            passou_cooldown = (agora - tempo_ultimo_sinal) > (COOLDOWN_MINUTOS * 60)
            
            if sinal_db != ultimo_sinal_enviado or passou_cooldown:
                notificar_telegram("SINAL", sinal_db, mensagem, fechamento_win, term_valor, distancia_vwap, tem_volume, tendencia_win, atr_atual, poc_atual)
                ultimo_sinal_enviado = sinal_db
                tempo_ultimo_sinal = agora
        # ---------------------------------------

        # LOG DA DECISÃO DO ALGORITMO
        log.info(f"WIN: {fechamento_win:.0f} | Termômetro: {term_valor:.2f} | Decisão: {sinal_db}")

        # 4. Salvar no Banco (core/database.py)
        dados_bd = (
            timestamp_db, fechamento_win, z_win, linha_atual[f'Z_{TICKER_SP}'], 
            linha_atual[f'Z_{TICKER_DXY}'], linha_atual[f'Z_{TICKER_VIX}'], 
            term_valor, sinal_db, vwap_atual, distancia_vwap, vol_atual, vol_media
        )
        salvar_leitura(conn, dados_bd)

        # =================================================================
        # 5. Interface Visual do Terminal (Restaurada)
        # =================================================================
        
        # Formatação Visual
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
        
        print("Aguardando 10 segundos... (Pressione 'T' para enviar ao Telegram)")

        # =================================================================
        # 6. Espera Inteligente (Hotkey Non-blocking)
        # =================================================================
        espera_segundos = 10
        tempo_inicial = time.time()
        
        while time.time() - tempo_inicial < espera_segundos:
            # Verifica se alguma tecla foi pressionada fisicamente no terminal
            if msvcrt.kbhit():
                tecla = msvcrt.getch().decode('utf-8', errors='ignore').lower()
                
                # Se a tecla for 't', aciona o Telegram imediatamente
                if tecla == 't':
                    print(f"\n{MAGENTA}🚀 [HOTKEY] Tecla 'T' acionada! Disparando envio manual...{RESET}")
                    # Usa a função do telegram_notifier que já instanciamos antes
                    notificar_telegram("VALIDAÇÃO MANUAL", sinal_db, mensagem, fechamento_win, term_valor, distancia_vwap, tem_volume, tendencia_win, atr_atual, poc_atual)
                    
                    # Limpa o buffer do teclado para não ler 't' duplicado e avisa na tela
                    while msvcrt.kbhit(): msvcrt.getch()
                    time.sleep(1) # Pausa rápida só para você conseguir ler o aviso na tela preta
            
            time.sleep(0.1) # Dorme 100ms a cada ciclo para não sobrecarregar a CPU

if __name__ == "__main__":
    main()