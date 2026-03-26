import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime

# 1. Inicializa a conexão com o MetaTrader 5 aberto na máquina
if not mt5.initialize():
    print("Falha ao inicializar o MT5. Verifique se o terminal está aberto.")
    mt5.shutdown()
    quit()

# 2. Define os parâmetros de busca
symbol = "WINJ26" # Substitua pelo ticker exato que está no seu MT5 (ex: VIX, DXY, WINFUT)
timeframe = mt5.TIMEFRAME_M5 # Gráfico de 5 minutos
num_bars = 100 # Quantidade de candles para o cálculo

# 3. Extrai os dados diretamente da memória do MT5 (zero latência)
rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, num_bars)

if rates is None:
    print(f"Erro ao puxar dados. Verifique se o ativo '{symbol}' está na janela de Observação do Mercado.")
    mt5.shutdown()
    quit()

# 4. Converte os dados brutos para um DataFrame do Pandas
df = pd.DataFrame(rates)
df['time'] = pd.to_datetime(df['time'], unit='s') # Converte o timestamp para data/hora legível
df.set_index('time', inplace=True)

# 5. Aplica a Matemática: Cálculo do Z-Score (Ex: janela de 20 períodos)
periodo = 20
df['Media_20'] = df['close'].rolling(window=periodo).mean()
df['Desvio_20'] = df['close'].rolling(window=periodo).std()

# Fórmula do Z-Score: (Preço Atual - Média) / Desvio Padrão
df['Z_Score'] = (df['close'] - df['Media_20']) / df['Desvio_20']

# Remove as linhas iniciais que ficaram sem cálculo de média (NaN)
df.dropna(inplace=True)

# Exibe as últimas 5 linhas com o resultado final
print(f"\n--- Dados e Z-Score para {symbol} (5M) ---")
print(df[['close', 'Media_20', 'Z_Score']].tail())

# 6. Encerra a conexão com o MT5
mt5.shutdown()