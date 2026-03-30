# diario_bordo.py
# EOD Tear Sheet (End-of-Day Report)
# Autor: Thiago Marques Meneses
# Data de Criação: 27/09/2024
# 
# Descrição:
# Este script é um "Diário de Bordo" para o pregão do dia. Ele se conecta ao banco de dados onde o sistema quantitativo armazena suas leituras e sinais, e gera um relatório detalhado do comportamento do mercado, desempenho do robô e insights estratégicos.
# O objetivo é fornecer uma visão clara e estruturada do que aconteceu durante o dia, destacando os momentos críticos, as decisões do sistema e o impacto do cenário macroeconômico.
# O relatório é impresso no terminal, utilizando cores para facilitar a leitura e destacar os pontos mais importantes. Ele é ideal para ser consultado ao final do pregão, mas pode ser rodado a qualquer momento para um resumo instantâneo do que aconteceu até então.
#
# Como Utilizar:
# Após as 18:25 (ou a qualquer momento do dia que você quiser um resumo instantâneo do que aconteceu até agora), 
# abra o terminal e rode: python diario_bordo.py


import sqlite3
import pandas as pd
from datetime import datetime
import os

# Cores para o Terminal
VERDE = '\033[92m'
VERMELHO = '\033[91m'
AMARELO = '\033[93m'
AZUL = '\033[96m'
RESET = '\033[0m'

def limpar_tela():
    os.system('cls' if os.name == 'nt' else 'clear')

def gerar_relatorio_fechamento():
    # Conecta no nosso "cofre" de dados
    conn = sqlite3.connect('dados_mercado.db')
    
    # Puxa APENAS as leituras do pregão de hoje
    query = '''
        SELECT * FROM historico_termometro 
        WHERE date(timestamp) = date('now', 'localtime')
    '''
    df = pd.read_sql_query(query, conn, parse_dates=['timestamp'])
    conn.close()

    limpar_tela()
    
    if df.empty:
        print(f"{AMARELO}Nenhum dado registrado no banco para o pregão de hoje.{RESET}")
        return

    # ==========================================
    # 1. PROCESSAMENTO DE DADOS (CRUNCHING)
    # ==========================================
    abertura = df['win_close'].iloc[0]
    fechamento = df['win_close'].iloc[-1]
    maxima = df['win_close'].max()
    minima = df['win_close'].min()
    variacao_pts = fechamento - abertura

    # Resumo de Ações do Robô
    sinais = df['sinal'].value_counts()
    qtd_compras = sinais.get('COMPRA', 0)
    qtd_vendas = sinais.get('VENDA', 0)
    qtd_bloqueios = sinais[sinais.index.str.contains('BLOQUEIO')].sum() if not sinais.empty else 0

    # Resumo do Impacto Externo (A Média da Maré)
    media_z_sp = df['z_sp500'].mean()
    media_z_dxy = df['z_dxy'].mean()
    media_term = df['termometro_score'].mean()

    # ==========================================
    # 2. INTELIGÊNCIA DE DIAGNÓSTICO
    # ==========================================
    if media_term >= 0.8:
        humor_dia = f"{VERDE}FORTEMENTE COMPRADOR (Apetite a Risco Global){RESET}"
    elif media_term <= -0.8:
        humor_dia = f"{VERMELHO}FORTEMENTE VENDEDOR (Aversão a Risco Global){RESET}"
    else:
        humor_dia = f"{AZUL}LATERAL / MISTO (Briga Institucional e Indecisão){RESET}"

    # ==========================================
    # 3. IMPRESSÃO DO RELATÓRIO (TEAR SHEET)
    # ==========================================
    print("="*75)
    print(f" 📓 DIÁRIO DE BORDO - FECHAMENTO DO PREGÃO ({datetime.now().strftime('%d/%m/%Y')})")
    print("="*75)
    
    print(f"📈 1. COMPORTAMENTO DO PREÇO (WIN):")
    print(f"   Abertura Registrada : {abertura:.0f}")
    print(f"   Fechamento/Atual    : {fechamento:.0f}")
    print(f"   Máxima do Dia       : {maxima:.0f}")
    print(f"   Mínima do Dia       : {minima:.0f}")
    
    cor_var = VERDE if variacao_pts > 0 else VERMELHO
    print(f"   Variação do Período : {cor_var}{variacao_pts:+.0f} pontos{RESET}\n")

    print(f"🌍 2. IMPACTO EXTERNO (Z-SCORE MÉDIO DA MARÉ):")
    print(f"   S&P 500 (EUA)   : {media_z_sp:+.2f}")
    print(f"   Dólar Global    : {media_z_dxy:+.2f}")
    print(f"   Veredito Macro  : {humor_dia}\n")

    print(f"🤖 3. DESEMPENHO DO MOTOR QUANTITATIVO:")
    print(f"   Ciclos de Leitura Analisados : {len(df)}")
    print(f"   Sinais de COMPRA Confirmados : {VERDE}{qtd_compras}{RESET}")
    print(f"   Sinais de VENDA Confirmados  : {VERMELHO}{qtd_vendas}{RESET}")
    print(f"   Armadilhas Bloqueadas        : {AMARELO}{qtd_bloqueios}{RESET} (Falta de Volume, VWAP, etc)\n")

    print("="*75)
    print(f"{AZUL}💡 INSIGHT DO SISTEMA E VEREDITO:{RESET}")
    
    # Heurística de Fechamento (O que o dia nos ensinou?)
    if qtd_bloqueios > (qtd_compras + qtd_vendas) * 2:
        print("   Hoje foi um dia de altíssima manipulação e ruído (Caixote).")
        print("   O sistema precisou agir massivamente na defensiva, bloqueando")
        print("   falsos rompimentos para proteger o seu capital contra o 'moedor de carne'.")
    elif media_term > 0.5 and variacao_pts < -300:
        print(f"   {MAGENTA}⚠️ DIVERGÊNCIA CRÍTICA IDENTIFICADA:{RESET}")
        print("   O exterior estava comprador o dia todo, mas o Brasil CAIU.")
        print("   Isso indica fortíssimo fluxo de saída local (Gringo vendendo B3")
        print("   ou risco político interno esmagando a correlação global).")
    elif media_term < -0.5 and variacao_pts > 300:
        print(f"   {MAGENTA}⚠️ DIVERGÊNCIA CRÍTICA IDENTIFICADA:{RESET}")
        print("   O exterior afundou, mas o Brasil SUBIU.")
        print("   Fluxo local de defesa agressivo. Institucionais brasileiros")
        print("   absorveram toda a oferta externa.")
    else:
        print("   Mercado técnico, previsível e alinhado.")
        print("   O índice seguiu a maré global perfeitamente, fluindo como")
        print("   água de acordo com os modelos matemáticos de risco.")
    print("="*75)

if __name__ == "__main__":
    gerar_relatorio_fechamento()