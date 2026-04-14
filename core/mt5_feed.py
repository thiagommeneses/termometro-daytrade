# Tudo relacionado à conexão com as corretoras
# A ponte com a Genial e a Zero Markets.

import MetaTrader5 as mt5
import pandas as pd
from core.config import cfg

# Caminhos das corretoras (Centralizados no .env)
CAMINHO_GENIAL = cfg.MT5_PATH_GENIAL
CAMINHO_ZERO = cfg.MT5_PATH_ZERO

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
        return df 
    else:
        return df[['close']].rename(columns={'close': ticker})