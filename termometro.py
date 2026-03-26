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

timeframe = mt5.TIMEFRAME_M5
barras = 100

# Cores para o Terminal (ANSI Codes)
VERDE = '\033[92m'
VERMELHO = '\033[91m'
AMARELO = '\033[93m'
RESET = '\033[0m'

# =================================================================
# INICIALIZAÇÃO DO BANCO DE DADOS (SQLITE)
# =================================================================
conn = sqlite3.connect('dados_mercado.db')
cursor = conn.cursor()

# Cria a tabela estruturada (Pronta para migrar pro Postgres no futuro)
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

# =================================================================
# FUNÇÕES DE APOIO
# =================================================================
def puxar_dados(ticker, caminho_exe):
    if not mt5.initialize(path=caminho_exe):
        return None
    rates = mt5.copy_rates_from_pos(ticker, timeframe, 0, barras)
    mt5.shutdown() 
    
    if rates is None:
        return None
        
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    return df[['close']].rename(columns={'close': ticker})

def limpar_tela():
    os.system('cls' if os.name == 'nt' else 'clear')

# =================================================================
# LOOP INFINITO (O CORAÇÃO DO SISTEMA)
# =================================================================

while True:
    limpar_tela()
    hora_atual = datetime.now().strftime("%H:%M:%S")
    print(f"🔄 Atualizando Dados do Mercado... [{hora_atual}]")

    # Extração
    df_win = puxar_dados(ticker_win, caminho_genial)
    df_vix = puxar_dados(ticker_vix, caminho_zero)
    df_dxy = puxar_dados(ticker_dxy, caminho_zero)
    df_sp  = puxar_dados(ticker_sp, caminho_zero)

    if any(df is None for df in [df_win, df_vix, df_dxy, df_sp]):
        print(f"{VERMELHO}Erro de conexão ou Ticker não encontrado no MT5.{RESET}")
        time.sleep(10) 
        continue

    # Cruzamento e Cálculo
    df_final = df_win.join([df_vix, df_dxy, df_sp]).dropna()
    periodo = 20

    for ativo in [ticker_win, ticker_vix, ticker_dxy, ticker_sp]:
        media = df_final[ativo].rolling(window=periodo).mean()
        desvio = df_final[ativo].rolling(window=periodo).std()
        df_final[f'Z_{ativo}'] = (df_final[ativo] - media) / desvio

    df_final.dropna(inplace=True)

    # Cálculo do Termômetro Global (S&P 40%, VIX 30%, DXY 30%)
    df_final['Termometro'] = (
        (df_final[f'Z_{ticker_sp}'] * 0.4) + 
        ((df_final[f'Z_{ticker_vix}'] * -1) * 0.3) + 
        ((df_final[f'Z_{ticker_dxy}'] * -1) * 0.3)
    )

    # Extrai a última linha
    linha_atual = df_final.iloc[-1]
    fechamento_candle = linha_atual.name.strftime("%H:%M")
    timestamp_db = linha_atual.name.strftime("%Y-%m-%d %H:%M:00") # Formato SQL
    
    term_valor = linha_atual['Termometro']
    z_win = linha_atual[f'Z_{ticker_win}']

    # Lógica do Sinal (Separando o visual do banco de dados)
    if term_valor >= 1.5:
        sinal_txt = f"{VERDE}██ COMPRA FORTE (Mercado Global Eufórico) ██{RESET}"
        sinal_db = "COMPRA FORTE"
    elif term_valor <= -1.5:
        sinal_txt = f"{VERMELHO}██ VENDA FORTE (Mercado Global em Pânico) ██{RESET}"
        sinal_db = "VENDA FORTE"
    elif term_valor >= 0.5:
        sinal_txt = f"{VERDE}↗️ Viés de Alta Global{RESET}"
        sinal_db = "ALTA"
    elif term_valor <= -0.5:
        sinal_txt = f"{VERMELHO}↘️ Viés de Baixa Global{RESET}"
        sinal_db = "BAIXA"
    else:
        sinal_txt = f"{AMARELO}⚪ NEUTRO (Sem direção clara){RESET}"
        sinal_db = "NEUTRO"

    # =================================================================
    # SALVANDO NO BANCO DE DADOS
    # =================================================================
    try:
        # Usa REPLACE para não duplicar caso o mesmo candle seja lido 2x
        cursor.execute('''
            INSERT OR REPLACE INTO historico_termometro 
            (timestamp, win_close, z_win, z_sp500, z_dxy, z_vix, termometro_score, sinal)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            timestamp_db,
            linha_atual[ticker_win],
            z_win,
            linha_atual[f'Z_{ticker_sp}'],
            linha_atual[f'Z_{ticker_dxy}'],
            linha_atual[f'Z_{ticker_vix}'],
            term_valor,
            sinal_db
        ))
        conn.commit()
    except Exception as e:
        print(f"Erro ao salvar no BD: {e}")

    # Impressão do Dashboard
    limpar_tela()
    print("="*60)
    print(f"   TERMÔMETRO MACRO QUANTITATIVO - 5 MINUTOS   ")
    print("="*60)
    print(f"Última Atualização: {hora_atual} | Ref. Candle: {fechamento_candle}\n")
    print(f"► SINAL ATUAL: {sinal_txt}\n")
    print(f"Pontuação do Termômetro Global: {term_valor:.2f}")
    print("-" * 60)
    print("RAIO-X DOS ATIVOS (Z-Score na Média de 20):")
    print(f"🇧🇷 Mini-índice (WIN) : {z_win:>5.2f} (Cotação: {linha_atual[ticker_win]:.0f})")
    print(f"🇺🇸 S&P 500           : {linha_atual[f'Z_{ticker_sp}']:>5.2f}")
    print(f"💵 Índice Dólar (DXY): {linha_atual[f'Z_{ticker_dxy}']:>5.2f}")
    print(f"😨 Índice Medo (VIX) : {linha_atual[f'Z_{ticker_vix}']:>5.2f}")
    print("="*60)
    print("Aguardando 60 segundos para próxima leitura...")

    time.sleep(60)