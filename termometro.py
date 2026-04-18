###################################################################
#  TERMOMETRO INSTITUCIONAL - MACRO + VWAP + 60M + VOLUME
#  Desenvolvido por: Thiago Marques Meneses (GitHub: /thiagommeneses)
#  Descrição: Este script é um termômetro institucional avançado que combina análise macroeconômica, VWAP, tendência de 60 minutos e fluxo de volume para fornecer sinais de compra e venda mais precisos. Ele coleta dados do MetaTrader 5, calcula indicadores e exibe um dashboard visual atualizado a cada 10 segundos.
#  Requisitos: MetaTrader 5, pandas, sqlite3, Python 3.x
#
# # Funcionalidades: 
# 1. Coleta de dados em tempo real do MT5 para WIN, VIX, DXY e S&P 500.
# 2. Cálculo do VWAP diário para o WIN e análise de distância do preço atual.
# 3. Análise de tendência de 60 minutos para WIN e S&P 500.
# 4. Cálculo do Z-Score para os ativos e composição de um termômetro institucional.
# 5. Lógica de sinal que combina todos os indicadores para confirmar ou bloquear operações.
# 6. Armazenamento histórico dos dados e sinais em um banco de dados SQLite.
# 7. Dashboard visual no terminal com interpretação do cenário atual e análise detalhada.
# 
# Motor Analítico:
#   Direção (Termômetro Macro: SP500, DXY, VIX)
#   Tendência Longa (Filtro 60M)
#   Localização Institucional (VWAP)
#   Verdade/Combustível (Volume)
###################################################################

import MetaTrader5 as mt5
import pandas as pd
import time
import os
import sqlite3
from datetime import datetime
from core.config import cfg

# 1. Configurações (Centralizadas no .env)
caminho_genial = cfg.MT5_PATH_GENIAL
caminho_zero = cfg.MT5_PATH_ZERO

ticker_win = cfg.TICKER_WIN
ticker_vix = cfg.TICKER_VIX
ticker_dxy = cfg.TICKER_DXY
ticker_sp  = cfg.TICKER_SP

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
conn = sqlite3.connect(cfg.DB_NAME)
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
        sinal TEXT,
        vwap REAL,
        dist_vwap_pts REAL,
        vol_atual REAL,
        vol_media REAL
    )
''')
conn.commit()

# =================================================================
# FUNÇÕES DE APOIO 
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
        return df 
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
    print(f"🔄 Lendo o mercado e gerando análise do cenário... [{hora_atual}]")

    df_win_full = puxar_dados(ticker_win, caminho_genial, mt5.TIMEFRAME_M5, 120, completo=True)
    df_vix = puxar_dados(ticker_vix, caminho_zero, mt5.TIMEFRAME_M5, 120)
    df_dxy = puxar_dados(ticker_dxy, caminho_zero, mt5.TIMEFRAME_M5, 120)
    df_sp  = puxar_dados(ticker_sp, caminho_zero, mt5.TIMEFRAME_M5, 120)

    df_win_60m = puxar_dados(ticker_win, caminho_genial, mt5.TIMEFRAME_H1, 25)
    df_sp_60m  = puxar_dados(ticker_sp, caminho_zero, mt5.TIMEFRAME_H1, 25)

    if any(df is None for df in [df_win_full, df_vix, df_dxy, df_sp, df_win_60m, df_sp_60m]):
        print(f"{VERMELHO}Erro de conexão ou Ticker não encontrado no MT5.{RESET}")
        time.sleep(10) 
        continue

    df_win_close = df_win_full[['close']].rename(columns={'close': ticker_win})

    # =================================================================
    # CÁLCULO DA GRAVIDADE (VWAP) E FLUXO (VOLUME)
    # =================================================================
    df_win_full['Date'] = df_win_full.index.date
    df_win_full['Typical_Price'] = (df_win_full['high'] + df_win_full['low'] + df_win_full['close']) / 3
    df_win_full['TP_Vol'] = df_win_full['Typical_Price'] * df_win_full['tick_volume']
    
    df_win_full['Cum_TP_Vol'] = df_win_full.groupby('Date')['TP_Vol'].cumsum()
    df_win_full['Cum_Vol'] = df_win_full.groupby('Date')['tick_volume'].cumsum()
    df_win_full['VWAP'] = df_win_full['Cum_TP_Vol'] / df_win_full['Cum_Vol']

    df_win_full['Vol_SMA20'] = df_win_full['tick_volume'].rolling(window=20).mean()

    vwap_atual = df_win_full['VWAP'].iloc[-1]
    fechamento_win = df_win_full['close'].iloc[-1]
    distancia_vwap = fechamento_win - vwap_atual
    
    vol_atual = float(df_win_full['tick_volume'].iloc[-1])
    vol_media = float(df_win_full['Vol_SMA20'].iloc[-1])
    tem_volume = vol_atual > vol_media

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
    # LÓGICA DO SINAL + INTELIGÊNCIA DO ANALISTA (INTERPRETAÇÃO)
    # =================================================================
    alerta_vwap = f"{MAGENTA}(Elástico Esticado){RESET}" if abs(distancia_vwap) > 500 else ""
    mensagem_interpretacao = ""

    # 1. Regra de Ouro: O Efeito Elástico tem prioridade no aviso
    if abs(distancia_vwap) > 500:
        sinal_txt = f"{AMARELO}⚠️ OPERAÇÃO BLOQUEADA (Preço muito esticado da VWAP){RESET}"
        sinal_db = "BLOQUEIO_ELASTICO"
        
        if distancia_vwap > 0:
            mensagem_interpretacao = "O mercado subiu demais e esticou da VWAP. Comprar agora é risco altíssimo de pegar o topo. A gravidade deve puxar o preço de volta. Aguarde um recuo."
        else:
            mensagem_interpretacao = "A tendência é de baixa, mas não venda agora no fundo. O preço caiu tanto que esticou da VWAP. A chance de um repique violento para cima é enorme."

    # 2. Cenários de Sinal Forte (Acima de 1.5 ou Abaixo de -1.5)
    elif term_valor >= 1.5:
        if tendencia_sp == "ALTA" and tendencia_win == "ALTA" and fechamento_win >= vwap_atual and tem_volume:
            sinal_txt = f"{VERDE}██ COMPRA CONFIRMADA ██{RESET}"
            sinal_db = "COMPRA"
            mensagem_interpretacao = "Cenário dos sonhos! O macro empurra, a maré de 60M apoia, estamos acima da VWAP e os tubarões estão colocando lote (volume alto). Siga o fluxo comprador!"
        elif not tem_volume:
            sinal_txt = f"{AMARELO}⚠️ COMPRA BLOQUEADA (Falta Volume){RESET}"
            sinal_db = "BLOQUEIO_VOL"
            mensagem_interpretacao = "O preço está subindo e o exterior apoia, mas cadê o dinheiro? O volume está abaixo da média. Cheira a falso rompimento (armadilha para pessoa física)."
        elif fechamento_win < vwap_atual:
            sinal_txt = f"{AMARELO}⚠️ COMPRA BLOQUEADA (VWAP){RESET}"
            sinal_db = "BLOQUEIO_VWAP"
            mensagem_interpretacao = "O exterior melhorou, mas internamente os institucionais ainda estão vendidos (preço abaixo da VWAP). Comprar agora é dar cabeçada no teto. Espere romper a VWAP."
        else:
            sinal_txt = f"{AMARELO}⚠️ COMPRA BLOQUEADA (60M){RESET}"
            sinal_db = "BLOQUEIO_H1"
            mensagem_interpretacao = "Isso parece um repique de alta dentro de uma maré de queda (60M caindo). Não seja herói comprando contra a tendência maior."

    elif term_valor <= -1.5:
        if tendencia_sp == "BAIXA" and tendencia_win == "BAIXA" and fechamento_win <= vwap_atual and tem_volume:
            sinal_txt = f"{VERMELHO}██ VENDA CONFIRMADA ██{RESET}"
            sinal_db = "VENDA"
            mensagem_interpretacao = "Cenário perfeito para venda! O mundo está caindo (S&P cai, DXY/VIX sobem), estamos abaixo da VWAP e o volume confirma o pânico. Venda a favor da gravidade."
        elif not tem_volume:
            sinal_txt = f"{AMARELO}⚠️ VENDA BLOQUEADA (Falta Volume){RESET}"
            sinal_db = "BLOQUEIO_VOL"
            mensagem_interpretacao = "O preço está caindo, mas sem volume expressivo bancando a queda. Pode ser apenas uma exaustão passageira. Cuidado para não vender o fundo do movimento."
        elif fechamento_win > vwap_atual:
            sinal_txt = f"{AMARELO}⚠️ VENDA BLOQUEADA (VWAP){RESET}"
            sinal_db = "BLOQUEIO_VWAP"
            mensagem_interpretacao = "O macro azedou, mas o preço médio dos grandes bancos (VWAP) está segurando a queda como um chão de concreto. Vender agora é perigoso. Fique de fora."
        else:
            sinal_txt = f"{AMARELO}⚠️ VENDA BLOQUEADA (60M){RESET}"
            sinal_db = "BLOQUEIO_H1"
            mensagem_interpretacao = "Isso é uma correção natural de baixa dentro de uma tendência forte de alta (60M subindo). Vender contra a maré agora é pedir para ser atropelado."

    # 3. Cenários de Viés e Lateralidade (-1.5 a 1.5)
    else:
        if term_valor >= 0.5:
            sinal_txt = f"{VERDE}↗️ Viés de Alta Global{RESET}"
            sinal_db = "ALTA"
            mensagem_interpretacao = "Existe um viés leve de alta no exterior, mas não é forte o suficiente para uma entrada agressiva. O mercado está 'cozinhando em banho-maria'."
        elif term_valor <= -0.5:
            sinal_txt = f"{VERMELHO}↘️ Viés de Baixa Global{RESET}"
            sinal_db = "BAIXA"
            mensagem_interpretacao = "O exterior pesa levemente para baixo. O mercado pode ir caindo devagar, de escadinha. Momento de proteger o capital e evitar compras pesadas."
        else:
            sinal_txt = f"{RESET}⚪ NEUTRO (Sem direção clara){RESET}"
            sinal_db = "NEUTRO"
            mensagem_interpretacao = "Robôs globais desligados ou brigando sem direção. O mercado está lateral, caótico e perigoso para operar. Lembre-se: Ficar de fora também é operar!"

    # =================================================================
    # SALVANDO NO BD
    # =================================================================
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO historico_termometro 
            (timestamp, win_close, z_win, z_sp500, z_dxy, z_vix, termometro_score, sinal, vwap, dist_vwap_pts, vol_atual, vol_media)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (timestamp_db, fechamento_win, z_win, linha_atual[f'Z_{ticker_sp}'], 
              linha_atual[f'Z_{ticker_dxy}'], linha_atual[f'Z_{ticker_vix}'], term_valor, sinal_db, vwap_atual, distancia_vwap, vol_atual, vol_media))
        conn.commit()
    except Exception as e:
        print(f"Erro BD: {e}")

    # =================================================================
    # DASHBOARD VISUAL
    # =================================================================
    limpar_tela()
    print("="*65)
    print(f"   TERMÔMETRO INSTITUCIONAL - MACRO + VWAP + 60M + VOLUME   ")
    print("="*65)
    print(f"Última Atualização: {hora_atual} | Ref. Candle: {fechamento_candle}\n")
    
    print(f"► SINAL ATUAL: {sinal_txt}\n")
    print(f"Pontuação Termômetro Global: {term_valor:.2f}")
    print("-" * 65)
    
    print(f"📊 FLUXO DE VOLUME (No Candle de 5M Atual):")
    cor_vol = VERDE if tem_volume else AMARELO
    status_vol_txt = "ACIMA da Média (Confirmado)" if tem_volume else "ABAIXO da Média (Movimento Oco)"
    print(f"   Status do Lote: {cor_vol}{status_vol_txt}{RESET}")
    print(f"   Vol. Atual: {vol_atual:.0f} | Vol. Médio: {vol_media:.0f}")
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
    
    # NOVA SEÇÃO: INTELIGÊNCIA DO ANALISTA
    print(f"{AZUL}💡 ANÁLISE DO CENÁRIO:{RESET}")
    print(f"   {mensagem_interpretacao}")
    print("="*65)
    
    print("RAIO-X DOS ATIVOS (Z-Score no 5M):")
    print(f"🇧🇷 WIN  : {z_win:>5.2f} (Cot: {fechamento_win:.0f})")
    print(f"🇺🇸 S&P  : {linha_atual[f'Z_{ticker_sp}']:>5.2f}")
    print(f"💵 DXY  : {linha_atual[f'Z_{ticker_dxy}']:>5.2f}")
    print(f"😨 VIX  : {linha_atual[f'Z_{ticker_vix}']:>5.2f}")
    print("="*65)
    print("Aguardando 10 segundos para próxima leitura...")

    time.sleep(10)