import os
import MetaTrader5 as mt5
from datetime import datetime

# Importando nossos módulos locais
from core.mt5_feed import puxar_dados, CAMINHO_GENIAL, CAMINHO_ZERO
from core.math_engine import calcular_dados_d1, variacao_overnight
from strategies.analise_leilao import gerar_relatorio_abertura
from core.config import cfg

# Configurações (Centralizadas no .env)
TICKER_WIN = cfg.TICKER_WIN
TICKER_DXY = cfg.TICKER_DXY
TICKER_SP  = cfg.TICKER_SP

def limpar_tela():
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    limpar_tela()
    print("⏳ Conectando aos terminais e processando o fechamento D-1...\n")

    # Precisamos de mais barras (ex: 500) para garantir que pegamos os dados de ontem completos
    df_win = puxar_dados(TICKER_WIN, CAMINHO_GENIAL, mt5.TIMEFRAME_M5, 500, completo=True)
    df_sp  = puxar_dados(TICKER_SP, CAMINHO_ZERO, mt5.TIMEFRAME_M5, 500, completo=True)
    df_dxy = puxar_dados(TICKER_DXY, CAMINHO_ZERO, mt5.TIMEFRAME_M5, 500, completo=True)

    if any(df is None for df in [df_win, df_sp, df_dxy]):
        print("\033[91mErro de conexão MT5. Verifique os terminais.\033[0m")
        return

    # Processamento D-1 (Ontem)
    fechamento_win_d1, vwap_win_d1 = calcular_dados_d1(df_win)
    
    # Processamento Overnight (Madrugada / Hoje)
    var_sp = variacao_overnight(df_sp)
    var_dxy = variacao_overnight(df_dxy)

    # Regras de Negócio e Interpretação
    contexto_d1, cor_d1, humor_global, cor_humor, vies_gap, analise = gerar_relatorio_abertura(
        fechamento_win_d1, vwap_win_d1, var_sp, var_dxy
    )

    # Imprimindo o Relatório Oficial
    limpar_tela()
    print("="*75)
    print(f" 🌅 RELATÓRIO QUANTITATIVO DE PRÉ-MERCADO (LEILÃO WIN) ")
    print("="*75)
    print(f"Data Base: {datetime.now().strftime('%d/%m/%Y')} | Ticker Analisado: {TICKER_WIN}\n")

    print(f"📊 1. O ESPELHO DE ONTEM (D-1):")
    print(f"   Preço de Fechamento : {fechamento_win_d1:.0f}")
    print(f"   VWAP Diária (D-1)   : {vwap_win_d1:.0f}")
    print(f"   Contexto Posicional : {cor_d1}{contexto_d1}\033[0m\n")

    print(f"🌍 2. O HUMOR GLOBAL AGORA (OVERNIGHT):")
    print(f"   S&P 500 Futuro      : {var_sp:+.2f}%")
    print(f"   Índice Dólar (DXY)  : {var_dxy:+.2f}%")
    print(f"   Veredito Macro      : {cor_humor}{humor_global}\033[0m\n")

    print("-" * 75)
    print(f"🎯 3. PROJEÇÃO DO LEILÃO E DIREÇÃO (09:00):")
    print(f"   {vies_gap}\n")
    print(f"   \033[96m💡 ANÁLISE DO CENÁRIO:\033[0m")
    print(f"   {analise}")
    print("="*75)

if __name__ == "__main__":
    main()