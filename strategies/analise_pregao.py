# A árvore de decisão e as mensagens do analista
# Aqui vive a inteligência artificial do seu analista heurístico.

from core.models import MarketContext, AnalysisResult

# Cores para o Terminal
VERDE = '\033[92m'
VERMELHO = '\033[91m'
AMARELO = '\033[93m'
AZUL = '\033[96m'
MAGENTA = '\033[95m'
RESET = '\033[0m'

def analisar_cenario_avancado(ctx: MarketContext) -> AnalysisResult:
    sinal_txt: str = ""
    sinal_db: str = ""
    mensagem: str = ""

    # Cálculos de Risco Baseados no ATR (Volatilidade Matemática)
    # Stop Loss de 1.5x o ATR protege contra violinadas. Alvo de 2x ATR.
    stop_loss = ctx.atr_atual * 1.5
    alvo = ctx.atr_atual * 2.0
    gestao_risco = f" | Stop Sugerido: {stop_loss:.0f} pts | Alvo: {alvo:.0f} pts"

    # 1. Filtro de Anomalia (O Brasil descolou do mundo?)
    if ctx.correlacao < 0:
        sinal_txt = f"{MAGENTA}⚠️ ALERTA DE DESCOLAMENTO (Anomalia Local){RESET}"
        sinal_db = "DESCOLAMENTO_MACRO"
        mensagem = f"A correlação com o S&P 500 quebrou (Corr: {ctx.correlacao:.2f}). O WIN parou de seguir o mundo, possivelmente devido a fluxo ou notícias locais. O Termômetro Global perde a eficácia aqui."
        return AnalysisResult(sinal_txt, sinal_db, mensagem)

    # 2. Regra de Ouro: Efeito Elástico e Atração do POC
    if abs(ctx.distancia_vwap) > 500:
        sinal_txt = f"{AMARELO}⚠️ OPERAÇÃO BLOQUEADA (Risco de Retorno à Média){RESET}"
        sinal_db = "BLOQUEIO_ELASTICO"
        if ctx.distancia_vwap > 0:
            mensagem = f"O mercado esticou demais para cima da VWAP. A região de maior volume do dia (POC) está lá em {ctx.poc_atual:.0f}. O risco de a gravidade puxar o preço de volta é imenso. [Risco de Retorno à Média]"
        else:
            mensagem = f"Não venda no fundo! Preço muito longe da VWAP. A chance de um repique violento buscando a POC ({ctx.poc_atual:.0f}) é altíssima."

    # 3. Sinais Institucionais Confirmados
    elif ctx.termometro >= 1.5:
        if ctx.tendencia_sp == "ALTA" and ctx.tendencia_win == "ALTA" and ctx.fechamento_win >= ctx.vwap_atual and ctx.tem_volume:
            sinal_txt = f"{VERDE}██ COMPRA INSTITUCIONAL CONFIRMADA ██{RESET}"
            sinal_db = "COMPRA"
            mensagem = f"Cenário Ouro: Macro empurrando, maré a favor, acima da VWAP com fluxo.{gestao_risco}"
        elif not ctx.tem_volume:
            sinal_txt = f"{AMARELO}⚠️ COMPRA BLOQUEADA (Movimento Oco){RESET}"
            sinal_db = "BLOQUEIO_VOL"
            mensagem = "Termômetro forte, mas os grandes players não estão comprando (falta volume). Cheira a armadilha."
        else:
            sinal_txt = f"{AMARELO}⚠️ COMPRA BLOQUEADA (Filtros Internos){RESET}"
            sinal_db = "BLOQUEIO_FILTROS"
            mensagem = "O exterior voa, mas o WIN não cruzou a VWAP ou a maré de 60M ainda é de baixa."

    elif ctx.termometro <= -1.5:
        if ctx.tendencia_sp == "BAIXA" and ctx.tendencia_win == "BAIXA" and ctx.fechamento_win <= ctx.vwap_atual and ctx.tem_volume:
            sinal_txt = f"{VERMELHO}██ VENDA INSTITUCIONAL CONFIRMADA ██{RESET}"
            sinal_db = "VENDA"
            mensagem = f"Cenário Ouro: Mundo derretendo, perdemos a VWAP e o volume vendedor confirmou.{gestao_risco}"
        elif not ctx.tem_volume:
            sinal_txt = f"{AMARELO}⚠️ VENDA BLOQUEADA (Movimento Oco){RESET}"
            sinal_db = "BLOQUEIO_VOL"
            mensagem = "O Termômetro despencou, mas a queda está sem fluxo financeiro pesado. Cuidado para não vender o fundo."
        else:
            sinal_txt = f"{AMARELO}⚠️ VENDA BLOQUEADA (Filtros Internos){RESET}"
            sinal_db = "BLOQUEIO_FILTROS"
            mensagem = "O macro é de pânico, mas internamente o preço ainda está forte (acima da VWAP ou 60M alta)."

    # 4. Mercado de Lado (Caixote)
    else:
        # Se o preço está muito perto da POC (Point of Control), o mercado está lateral e consolidado
        dist_poc = abs(ctx.fechamento_win - ctx.poc_atual)
        if dist_poc < 100:
            sinal_txt = f"{AZUL}💤 MERCADO EM CAIXOTE (Preso na POC){RESET}"
            sinal_db = "NEUTRO_CAIXOTE"
            mensagem = f"Preço girando exatamente na zona de maior volume do dia (POC: {ctx.poc_atual:.0f}). Zona de briga de grandes lotes. Evite operar aqui no meio."
        elif ctx.termometro >= 0.5:
            sinal_txt = f"{VERDE}↗️ Viés Leve de Alta{RESET}"
            sinal_db = "ALTA"
            mensagem = "Exterior com leve apetite a risco. Aguarde alinhamento de VWAP e Fluxo para entrar."
        elif ctx.termometro <= -0.5:
            sinal_txt = f"{VERMELHO}↘️ Viés Leve de Baixa{RESET}"
            sinal_db = "BAIXA"
            mensagem = "Pressão externa é vendedora, mas sem força institucional clara ainda."
        else:
            sinal_txt = f"{RESET}⚪ NEUTRO (Briga de Robôs){RESET}"
            sinal_db = "NEUTRO"
            mensagem = "Fatores globais e locais totalmente anulados. Ficar de fora preserva o seu capital."

    # A MÁGICA ACONTECE AQUI: Injeção do Contexto Macro Histórico
    # O sinal continua sendo de COMPRA/VENDA, mas a mensagem ganha o dossiê da notícia.
    if ctx.alerta_macro:
        mensagem = f"{MAGENTA}{ctx.alerta_macro}{RESET}\n   {AZUL}💡 Análise Técnica:{RESET} {mensagem}"

    return AnalysisResult(sinal_txt, sinal_db, mensagem)