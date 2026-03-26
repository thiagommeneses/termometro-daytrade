import MetaTrader5 as mt5
import pandas as pd

# 1. Configurações com os caminhos exatos da sua máquina
caminho_genial = r"C:\Program Files\MetaTrader 5\terminal64.exe"
caminho_zero = r"C:\Program Files\Zero Financial MT5 Terminal\terminal64.exe"

# Tickers (Verifique se são exatamente esses os nomes na janela de Observação do Mercado)
ticker_win = "WINJ26" # Genial (Pode ser WINFUT ou WIN$ dependendo de como você operou hoje)
ticker_vix = "VIX"    # Zero Markets (Pode estar como VIX.c, VOLX, etc.)
ticker_dxy = "USDX"    # Zero Markets (Pode estar como USDX)

timeframe = mt5.TIMEFRAME_M5
barras = 100

# 2. Função para conectar em um MT5 específico e puxar o dado
def puxar_dados(ticker, caminho_exe):
    # Inicializa passando o caminho exato do executável
    if not mt5.initialize(path=caminho_exe):
        print(f"Erro ao abrir MT5 em: {caminho_exe}")
        return None
    
    # Extrai os dados
    rates = mt5.copy_rates_from_pos(ticker, timeframe, 0, barras)
    
    # Encerra a conexão para liberar o Python para o próximo terminal
    mt5.shutdown() 
    
    if rates is None:
        print(f"Erro: Não encontrei '{ticker}'. Ele está na janela 'Observação do Mercado'?")
        return None
        
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    
    # Retorna apenas a coluna de fechamento com o nome do ticker
    return df[['close']].rename(columns={'close': ticker})

# 3. Executando o Switch entre os terminais
print("Conectando na Genial e extraindo WIN...")
df_win = puxar_dados(ticker_win, caminho_genial)

print("Conectando na Zero Markets e extraindo VIX / DXY...")
df_vix = puxar_dados(ticker_vix, caminho_zero)
df_dxy = puxar_dados(ticker_dxy, caminho_zero)

# Verifica se algum dado falhou antes de continuar
if df_win is None or df_vix is None or df_dxy is None:
    print("\nProcesso interrompido. Verifique os nomes dos tickers no MT5.")
    quit()

# 4. Cruzamento dos Dados
# Junta as tabelas. O dropna() remove os horários em que os três não estavam abertos juntos
df_final = df_win.join([df_vix, df_dxy]).dropna()

# 5. Cálculo do Z-Score e do Termômetro
periodo = 20

for ativo in [ticker_win, ticker_vix, ticker_dxy]:
    media = df_final[ativo].rolling(window=periodo).mean()
    desvio = df_final[ativo].rolling(window=periodo).std()
    df_final[f'Z_{ativo}'] = (df_final[ativo] - media) / desvio

# Remove as linhas iniciais que ficaram sem cálculo (NaN)
df_final.dropna(inplace=True)

# Calcula o Termômetro 
# Pesos: 50% VIX e 50% DXY (multiplicados por -1 pois sobem quando a bolsa cai)
df_final['Termometro'] = ((df_final[f'Z_{ticker_vix}'] * -1) * 0.5) + ((df_final[f'Z_{ticker_dxy}'] * -1) * 0.5)

print("\n--- SINAL DO TERMÔMETRO (Últimos 5 períodos) ---")
print(df_final[[ticker_win, f'Z_{ticker_win}', 'Termometro']].tail())