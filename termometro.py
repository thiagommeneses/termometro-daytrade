import MetaTrader5 as mt5
import pandas as pd
import time
import os
import sqlite3
from datetime import datetime

# 1. Configurações de Diretórios e Tickers
caminho_genial = r"C:\Program Files\MetaTrader 5\terminal64.exe"
caminho_zero = r"C:\Program Files\Zero Financial MT5 Terminal\terminal64.exe"

ticker_win = "WINJ26" 
ticker_vix = "VIX"    
ticker_dxy = "USDX"   
ticker_sp  = "US500"  

# Cores para o Terminal
VERDE = '\033[92m'
VERMELHO = '\033[91m'
AMARELO = '\033[93m'
AZUL = '\033[96m'
MAGENTA = '\033[95m'
RESET = '\033[0m'

# =================================================================
# INICIALIZAÇÃO DO BANCO DE DADOS (SQLITE)
# =================================================================
conn = sqlite3.connect('dados_mercado.db')
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS historico_termometro (
        timestamp DATETIME PRIMARY KEY,
        win_close REAL,
        z_win REAL,
        z_sp500 REAL,
        z_dxy REAL,
        z_vix REAL,
        termometro_score REAL,
        sinal TEXT
    )
''')
conn.commit()

# Tenta adicionar as novas colunas da VWAP caso elas não existam (Evolução do BD)
try:
    cursor.execute("ALTER TABLE historico_termometro ADD COLUMN vwap REAL")
    cursor.execute("ALTER TABLE historico_termometro ADD COLUMN dist_vwap_pts REAL")
    conn.commit()
except sqlite3.OperationalError:
    pass # As colunas já existem, segue o jogo.

# =================================================================
# FUNÇÕES DE APOIO ATUALIZADA (Agora puxa o Volume se necessário)
# =================================================================
def puxar_dados(ticker, caminho_exe, tf, num_barras, completo=False):
    if not mt5.initialize(path=caminho_exe):
        return None
    rates = mt5.copy_rates_from_pos(ticker, tf, 0, num_barras)
    mt5.shutdown() 
    
    if rates is None:
        return None
        
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    
    if completo:
        return df # Retorna OHLC e Volume
    else:
        return df[['close']].rename(columns={'close': ticker})

def limpar_tela():
    os.system('cls' if os.name == 'nt' else 'clear')

# =================================================================
# LOOP INFINITO 
# =================================================================

while True:
    limpar_tela()
    hora_atual = datetime.now().strftime("%H:%M:%S")
    print(f"🔄 Calculando Z-Score, Tendência H1 e VWAP Diária... [{hora_atual}]")

    # Extração 5 Minutos (Para o Z-Score)
    # Puxamos 120 barras para garantir que temos o dia todo para a VWAP (10 horas de pregão)
    df_win_full = puxar_dados(ticker_win, caminho_genial, mt5.TIMEFRAME_M5, 120, completo=True)
    df_vix = puxar_dados(ticker_vix, caminho_zero, mt5.TIMEFRAME_M5, 120)
    df_dxy = puxar_dados(ticker_dxy, caminho_zero, mt5.TIMEFRAME_M5, 120)
    df_sp  = puxar_dados(ticker_sp, caminho_zero, mt5.TIMEFRAME_M5, 120)

    # Extração 60 Minutos
    df_win_60m = puxar_dados(ticker_win, caminho_genial, mt5.TIMEFRAME_H1, 25)
    df_sp_60m  = puxar_dados(ticker_sp, caminho_zero, mt5.TIMEFRAME_H1, 25)

    if any(df is None for df in [df_win_full, df_vix, df_dxy, df_sp, df_win_60m, df_sp_60m]):
        print(f"{VERMELHO}Erro de conexão ou Ticker não encontrado no MT5.{RESET}")
        time.sleep(10) 
        continue

    # Isola apenas o fechamento do WIN para o cálculo do Z-Score
    df_win_close = df_win_full[['close']].rename(columns={'close': ticker_win})

    # =================================================================
    # CÁLCULO DA GRAVIDADE INSTITUCIONAL (VWAP DIÁRIA)
    # =================================================================
    # 1. Isola as datas para calcular a VWAP apenas com os dados de "HOJE"
    df_win_full['Date'] = df_win_full.index.date
    
    # 2. Preço Típico = (Máxima + Mínima + Fechamento) / 3
    df_win_full['Typical_Price'] = (df_win_full['high'] + df_win_full['low'] + df_win_full['close']) / 3
    
    # 3. Multiplica o Preço pelo Volume daquela barra de 5 minutos
    df_win_full['TP_Vol'] = df_win_full['Typical_Price'] * df_win_full['tick_volume']
    
    # 4. Soma Cumulativa do dia
    df_win_full['Cum_TP_Vol'] = df_win_full.groupby('Date')['TP_Vol'].cumsum()
    df_win_full['Cum_Vol'] = df_win_full.groupby('Date')['tick_volume'].cumsum()
    
    # 5. A Fórmula final da VWAP
    df_win_full['VWAP'] = df_win_full['Cum_TP_Vol'] / df_win_full['Cum_Vol']

    vwap_atual = df_win_full['VWAP'].iloc[-1]
    fechamento_win = df_win_full['close'].iloc[-1]
    distancia_vwap = fechamento_win - vwap_atual

    # =================================================================
    # CÁLCULO DA TENDÊNCIA 60M E Z-SCORE 5M
    # =================================================================
    sma_win_60m = df_win_60m[ticker_win].rolling(window=20).mean().iloc[-1]
    tendencia_win = "ALTA" if df_win_60m.iloc[-1][ticker_win] > sma_win_60m else "BAIXA"

    sma_sp_60m = df_sp_60m[ticker_sp].rolling(window=20).mean().iloc[-1]
    tendencia_sp = "ALTA" if df_sp_60m.iloc[-1][ticker_sp] > sma_sp_60m else "BAIXA"

    df_final = df_win_close.join([df_vix, df_dxy, df_sp]).dropna()
    periodo_z = 20

    for ativo in [ticker_win, ticker_vix, ticker_dxy, ticker_sp]:
        media = df_final[ativo].rolling(window=periodo_z).mean()
        desvio = df_final[ativo].rolling(window=periodo_z).std()
        df_final[f'Z_{ativo}'] = (df_final[ativo] - media) / desvio

    df_final.dropna(inplace=True)
    df_final['Termometro'] = (
        (df_final[f'Z_{ticker_sp}'] * 0.4) + 
        ((df_final[f'Z_{ticker_vix}'] * -1) * 0.3) + 
        ((df_final[f'Z_{ticker_dxy}'] * -1) * 0.3)
    )

    linha_atual = df_final.iloc[-1]
    fechamento_candle = linha_atual.name.strftime("%H:%M")
    timestamp_db = linha_atual.name.strftime("%Y-%m-%d %H:%M:00") 
    term_valor = linha_atual['Termometro']
    z_win = linha_atual[f'Z_{ticker_win}']

    # =================================================================
    # LÓGICA DO SINAL + VWAP + 60M
    # =================================================================
    alerta_vwap = ""
    if abs(distancia_vwap) > 500:
        alerta_vwap = f"{MAGENTA}(CUIDADO: Efeito Elástico! Preço esticado da VWAP){RESET}"

    if term_valor >= 1.5:
        if tendencia_sp == "ALTA" and tendencia_win == "ALTA" and fechamento_win >= vwap_atual:
            sinal_txt = f"{VERDE}██ COMPRA FORTE (Apoiada pelo 60M e VWAP) ██ {alerta_vwap}{RESET}"
            sinal_db = "COMPRA CONFIRMADA"
        else:
            sinal_txt = f"{AMARELO}⚠️ COMPRA BLOQUEADA (Filtro 60M ou abaixo da VWAP Institucional){RESET}"
            sinal_db = "COMPRA BLOQUEADA"
            
    elif term_valor <= -1.5:
        if tendencia_sp == "BAIXA" and tendencia_win == "BAIXA" and fechamento_win <= vwap_atual:
            sinal_txt = f"{VERMELHO}██ VENDA FORTE (Apoiada pelo 60M e VWAP) ██ {alerta_vwap}{RESET}"
            sinal_db = "VENDA CONFIRMADA"
        else:
            sinal_txt = f"{AMARELO}⚠️ VENDA BLOQUEADA (Filtro 60M ou acima da VWAP Institucional){RESET}"
            sinal_db = "VENDA BLOQUEADA"
            
    elif term_valor >= 0.5:
        sinal_txt = f"{VERDE}↗️ Viés de Alta Global{RESET}"
        sinal_db = "ALTA"
    elif term_valor <= -0.5:
        sinal_txt = f"{VERMELHO}↘️ Viés de Baixa Global{RESET}"
        sinal_db = "BAIXA"
    else:
        sinal_txt = f"{RESET}⚪ NEUTRO (Sem direção clara){RESET}"
        sinal_db = "NEUTRO"

    # Salvando no Banco de Dados
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO historico_termometro 
            (timestamp, win_close, z_win, z_sp500, z_dxy, z_vix, termometro_score, sinal, vwap, dist_vwap_pts)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (timestamp_db, fechamento_win, z_win, linha_atual[f'Z_{ticker_sp}'], 
              linha_atual[f'Z_{ticker_dxy}'], linha_atual[f'Z_{ticker_vix}'], term_valor, sinal_db, vwap_atual, distancia_vwap))
        conn.commit()
    except Exception as e:
        print(f"Erro BD: {e}")

    # =================================================================
    # DASHBOARD VISUAL
    # =================================================================
    limpar_tela()
    print("="*65)
    print(f"   TERMÔMETRO QUANTITATIVO - MACRO + VWAP + 60M   ")
    print("="*65)
    print(f"Última Atualização: {hora_atual} | Ref. Candle: {fechamento_candle}\n")
    
    print(f"► SINAL ATUAL: {sinal_txt}\n")
    print(f"Pontuação Termômetro Global: {term_valor:.2f}")
    print("-" * 65)
    
    print(f"🧲 GRAVIDADE INSTITUCIONAL (VWAP Diária):")
    status_vwap = f"{VERDE}Preço Acima (Comprados no Controle){RESET}" if distancia_vwap > 0 else f"{VERMELHO}Preço Abaixo (Vendidos no Controle){RESET}"
    print(f"   VWAP Atual   : {vwap_atual:.0f}")
    print(f"   Distância    : {distancia_vwap:+.0f} pontos -> {status_vwap}")
    print("-" * 65)

    print(f"🌊 FILTRO MACRO (Tendência 60 Minutos):")
    cor_win_60 = VERDE if tendencia_win == "ALTA" else VERMELHO
    cor_sp_60 = VERDE if tendencia_sp == "ALTA" else VERMELHO
    print(f"   Maré Local (WIN)  : {cor_win_60}{tendencia_win}{RESET}")
    print(f"   Maré Global (S&P) : {cor_sp_60}{tendencia_sp}{RESET}")
    print("-" * 65)
    
    print("RAIO-X DOS ATIVOS (Z-Score no 5M):")
    print(f"🇧🇷 WIN  : {z_win:>5.2f} (Cot: {fechamento_win:.0f})")
    print(f"🇺🇸 S&P  : {linha_atual[f'Z_{ticker_sp}']:>5.2f}")
    print(f"💵 DXY  : {linha_atual[f'Z_{ticker_dxy}']:>5.2f}")
    print(f"😨 VIX  : {linha_atual[f'Z_{ticker_vix}']:>5.2f}")
    print("="*65)
    print("Aguardando 10 segundos para próxima leitura...")

    time.sleep(10)