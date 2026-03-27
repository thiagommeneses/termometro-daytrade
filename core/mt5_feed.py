# Tudo relacionado à conexão com as corretoras
# A ponte com a Genial e a Zero Markets.

import MetaTrader5 as mt5
import pandas as pd

# Caminhos exatos das suas corretoras
CAMINHO_GENIAL = r"C:\Program Files\MetaTrader 5\terminal64.exe"
CAMINHO_ZERO = r"C:\Program Files\Zero Financial MT5 Terminal\terminal64.exe"

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