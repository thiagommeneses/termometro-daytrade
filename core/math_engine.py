# Cálculos puros (Z-Score, VWAP, Médias)
# Apenas matemática bruta. Entra DataFrame, sai número.

from datetime import datetime
import pandas as pd
import numpy as np
from typing import Tuple, Optional

def calcular_vwap_e_volume(df_full: pd.DataFrame) -> Tuple[float, float, float]:
    df = df_full.copy()
    df['Date'] = df.index.date
    df['Typical_Price'] = (df['high'] + df['low'] + df['close']) / 3
    df['TP_Vol'] = df['Typical_Price'] * df['tick_volume']
    
    df['Cum_TP_Vol'] = df.groupby('Date')['TP_Vol'].cumsum()
    df['Cum_Vol'] = df.groupby('Date')['tick_volume'].cumsum()
    df['VWAP'] = df['Cum_TP_Vol'] / df['Cum_Vol']

    df['Vol_SMA20'] = df['tick_volume'].rolling(window=20).mean()

    vwap_atual = float(df['VWAP'].iloc[-1])
    vol_atual = float(df['tick_volume'].iloc[-1])
    vol_media = float(df['Vol_SMA20'].iloc[-1])
    
    return vwap_atual, vol_atual, vol_media

def calcular_zscore_e_termometro(
    df_win_close: pd.DataFrame, 
    df_vix: pd.DataFrame, 
    df_dxy: pd.DataFrame, 
    df_sp: pd.DataFrame, 
    ticker_win: str, 
    ticker_sp: str, 
    ticker_dxy: str, 
    ticker_vix: str, 
    periodo_z: int = 20
) -> pd.DataFrame:
    df_final = df_win_close.join([df_vix, df_dxy, df_sp]).dropna()
    
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
    return df_final

def calcular_tendencia_60m(df_60m: pd.DataFrame, ticker: str) -> str:
    sma_60m = df_60m[ticker].rolling(window=20).mean().iloc[-1]
    return "ALTA" if df_60m.iloc[-1][ticker] > sma_60m else "BAIXA"

# (Mantenha as funções que já existem lá e adicione estas no final)

def calcular_dados_d1(df_m5: pd.DataFrame) -> Tuple[Optional[float], Optional[float]]:
    """Calcula o Fechamento e a VWAP exata do dia anterior (D-1) à prova de leilão"""
    df = df_m5.copy()
    df['Date'] = df.index.date
    datas_unicas = df['Date'].unique()

    if len(datas_unicas) == 0: return None, None

    hoje = datetime.now().date()
    
    # Inteligência de Calendário: Verifica se o mercado já abriu hoje
    if datas_unicas[-1] == hoje:
        # Já tem dados de hoje, então D-1 é o penúltimo
        data_d1 = datas_unicas[-2] if len(datas_unicas) >= 2 else datas_unicas[-1]
    else:
        # Mercado B3 fechado (antes das 09h), a última data da base já é o D-1!
        data_d1 = datas_unicas[-1]

    df_d1 = df[df['Date'] == data_d1].copy()

    df_d1['Typical_Price'] = (df_d1['high'] + df_d1['low'] + df_d1['close']) / 3
    df_d1['TP_Vol'] = df_d1['Typical_Price'] * df_d1['tick_volume']
    
    # Proteção contra divisão por zero
    soma_vol = df_d1['tick_volume'].sum()
    vwap_d1 = df_d1['TP_Vol'].sum() / soma_vol if soma_vol > 0 else df_d1['close'].iloc[-1]

    fechamento_d1 = df_d1['close'].iloc[-1]

    return fechamento_d1, vwap_d1

def variacao_overnight(df_m5: pd.DataFrame) -> float:
    """Calcula a variação % do ativo global na madrugada"""
    df = df_m5.copy()
    df['Date'] = df.index.date
    datas_unicas = df['Date'].unique()
    
    if len(datas_unicas) < 2: return 0.0

    hoje = datetime.now().date()
    
    if datas_unicas[-1] == hoje:
        data_d1 = datas_unicas[-2]
    else:
        data_d1 = datas_unicas[-1]

    fechamento_d1 = df[df['Date'] == data_d1]['close'].iloc[-1]
    preco_atual = df['close'].iloc[-1]

    if fechamento_d1 == 0: return 0.0

    variacao_pct = ((preco_atual - fechamento_d1) / fechamento_d1) * 100
    return variacao_pct

def calcular_atr(df_m5: pd.DataFrame, periodo: int = 14) -> float:
    """Calcula o Average True Range (Volatilidade/Respiração do Mercado) para o Stop Loss"""
    df = df_m5.copy()
    df['Prev_Close'] = df['close'].shift(1)
    
    # True Range é o maior valor entre 3 medidas de volatilidade
    tr1 = df['high'] - df['low']
    tr2 = (df['high'] - df['Prev_Close']).abs()
    tr3 = (df['low'] - df['Prev_Close']).abs()
    
    df['TR'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['ATR'] = df['TR'].rolling(window=periodo).mean()
    
    return df['ATR'].iloc[-1]

def calcular_poc_intradiario(df_m5: pd.DataFrame) -> float:
    """Aproximação do Point of Control (POC): Onde houve mais volume no dia"""
    df = df_m5.copy()
    hoje = datetime.now().date()
    df_hoje = df[df.index.date == hoje].copy()
    
    if df_hoje.empty: 
        return df['close'].iloc[-1]

    # Agrupa os preços em "caixotes" de 50 pontos e soma o volume dentro deles
    df_hoje['Price_Bin'] = (df_hoje['close'] / 50).round() * 50
    poc_profile = df_hoje.groupby('Price_Bin')['tick_volume'].sum()
    poc_price = poc_profile.idxmax()
    
    return poc_price

def calcular_correlacao_sp(df_win: pd.DataFrame, df_sp: pd.DataFrame, periodo: int = 20) -> float:
    """Calcula a Correlação de Pearson entre o Brasil e o S&P 500"""
    # Pega os nomes das colunas dinamicamente (evita hardcode de ticker)
    col_win = df_win.columns[0]
    col_sp = df_sp.columns[0]
    
    # Junta os dois DataFrames pela hora exata
    df_merged = pd.concat([df_win[col_win], df_sp[col_sp]], axis=1).dropna()
    
    if len(df_merged) < periodo: 
        return 1.0 # Se não tiver dados suficientes, assume correlação positiva padrão
        
    corr = df_merged[col_win].rolling(window=periodo).corr(df_merged[col_sp]).iloc[-1]
    return corr