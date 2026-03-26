# Cálculos puros (Z-Score, VWAP, Médias)
# Apenas matemática bruta. Entra DataFrame, sai número.

import pandas as pd

def calcular_vwap_e_volume(df_full):
    df = df_full.copy()
    df['Date'] = df.index.date
    df['Typical_Price'] = (df['high'] + df['low'] + df['close']) / 3
    df['TP_Vol'] = df['Typical_Price'] * df['tick_volume']
    
    df['Cum_TP_Vol'] = df.groupby('Date')['TP_Vol'].cumsum()
    df['Cum_Vol'] = df.groupby('Date')['tick_volume'].cumsum()
    df['VWAP'] = df['Cum_TP_Vol'] / df['Cum_Vol']

    df['Vol_SMA20'] = df['tick_volume'].rolling(window=20).mean()

    vwap_atual = df['VWAP'].iloc[-1]
    vol_atual = df['tick_volume'].iloc[-1]
    vol_media = df['Vol_SMA20'].iloc[-1]
    
    return vwap_atual, vol_atual, vol_media

def calcular_zscore_e_termometro(df_win_close, df_vix, df_dxy, df_sp, ticker_win, ticker_sp, ticker_dxy, ticker_vix, periodo_z=20):
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

def calcular_tendencia_60m(df_60m, ticker):
    sma_60m = df_60m[ticker].rolling(window=20).mean().iloc[-1]
    return "ALTA" if df_60m.iloc[-1][ticker] > sma_60m else "BAIXA"

# (Mantenha as funções que já existem lá e adicione estas no final)

def calcular_dados_d1(df_m5):
    """Calcula o Fechamento e a VWAP exata do dia anterior (D-1)"""
    df = df_m5.copy()
    df['Date'] = df.index.date
    datas_unicas = df['Date'].unique()

    if len(datas_unicas) < 2:
        return None, None # Precisa de pelo menos 2 dias no DataFrame

    # Isola apenas os dados de D-1 (o penúltimo dia na lista de datas)
    data_d1 = datas_unicas[-2]
    df_d1 = df[df['Date'] == data_d1].copy()

    # VWAP do D-1 (Matemática pura)
    df_d1['Typical_Price'] = (df_d1['high'] + df_d1['low'] + df_d1['close']) / 3
    df_d1['TP_Vol'] = df_d1['Typical_Price'] * df_d1['tick_volume']
    vwap_d1 = df_d1['TP_Vol'].sum() / df_d1['tick_volume'].sum()

    fechamento_d1 = df_d1['close'].iloc[-1]

    return fechamento_d1, vwap_d1

def variacao_overnight(df_m5):
    """Calcula a variação % do ativo em relação ao fechamento do dia anterior"""
    df = df_m5.copy()
    df['Date'] = df.index.date
    datas_unicas = df['Date'].unique()
    
    if len(datas_unicas) < 2: 
        return 0.0

    data_d1 = datas_unicas[-2]
    fechamento_d1 = df[df['Date'] == data_d1]['close'].iloc[-1]
    preco_atual = df['close'].iloc[-1]

    variacao_pct = ((preco_atual - fechamento_d1) / fechamento_d1) * 100
    return variacao_pct