# A árvore de decisão e as mensagens do analista
# Aqui vive a inteligência artificial do seu analista heurístico.

# Cores para o Terminal
VERDE = '\033[92m'
VERMELHO = '\033[91m'
AMARELO = '\033[93m'
MAGENTA = '\033[95m'
RESET = '\033[0m'

def analisar_cenario(term_valor, tendencia_sp, tendencia_win, fechamento_win, vwap_atual, tem_volume, distancia_vwap):
    sinal_txt = ""
    sinal_db = ""
    mensagem = ""

    # 1. Regra de Ouro: Efeito Elástico
    if abs(distancia_vwap) > 500:
        sinal_txt = f"{AMARELO}⚠️ OPERAÇÃO BLOQUEADA (Preço muito esticado da VWAP){RESET}"
        sinal_db = "BLOQUEIO_ELASTICO"
        if distancia_vwap > 0:
            mensagem = "O mercado subiu demais e esticou da VWAP. Comprar agora é risco altíssimo de pegar o topo. A gravidade deve puxar o preço de volta."
        else:
            mensagem = "A tendência é de baixa, mas não venda agora no fundo. O preço caiu tanto que esticou da VWAP. A chance de um repique violento para cima é enorme."

    # 2. Sinais Fortes
    elif term_valor >= 1.5:
        if tendencia_sp == "ALTA" and tendencia_win == "ALTA" and fechamento_win >= vwap_atual and tem_volume:
            sinal_txt = f"{VERDE}██ COMPRA CONFIRMADA ██{RESET}"
            sinal_db = "COMPRA"
            mensagem = "Cenário dos sonhos! O macro empurra, a maré de 60M apoia, estamos acima da VWAP e há volume. Siga o fluxo comprador!"
        elif not tem_volume:
            sinal_txt = f"{AMARELO}⚠️ COMPRA BLOQUEADA (Falta Volume){RESET}"
            sinal_db = "BLOQUEIO_VOL"
            mensagem = "O preço sobe e o exterior apoia, mas o volume está baixo. Cheira a falso rompimento (armadilha)."
        elif fechamento_win < vwap_atual:
            sinal_txt = f"{AMARELO}⚠️ COMPRA BLOQUEADA (VWAP){RESET}"
            sinal_db = "BLOQUEIO_VWAP"
            mensagem = "O exterior melhorou, mas internamente os institucionais ainda estão vendidos (abaixo da VWAP). Espere romper a VWAP."
        else:
            sinal_txt = f"{AMARELO}⚠️ COMPRA BLOQUEADA (60M){RESET}"
            sinal_db = "BLOQUEIO_H1"
            mensagem = "Isso parece um repique de alta dentro de uma maré de queda (60M caindo). Não compre contra a tendência maior."

    elif term_valor <= -1.5:
        if tendencia_sp == "BAIXA" and tendencia_win == "BAIXA" and fechamento_win <= vwap_atual and tem_volume:
            sinal_txt = f"{VERMELHO}██ VENDA CONFIRMADA ██{RESET}"
            sinal_db = "VENDA"
            mensagem = "Cenário perfeito para venda! O mundo cai, estamos abaixo da VWAP e o volume confirma o pânico."
        elif not tem_volume:
            sinal_txt = f"{AMARELO}⚠️ VENDA BLOQUEADA (Falta Volume){RESET}"
            sinal_db = "BLOQUEIO_VOL"
            mensagem = "Preço caindo sem volume expressivo. Pode ser exaustão. Cuidado para não vender o fundo."
        elif fechamento_win > vwap_atual:
            sinal_txt = f"{AMARELO}⚠️ VENDA BLOQUEADA (VWAP){RESET}"
            sinal_db = "BLOQUEIO_VWAP"
            mensagem = "O macro azedou, mas o preço médio (VWAP) está segurando a queda. Vender agora é perigoso."
        else:
            sinal_txt = f"{AMARELO}⚠️ VENDA BLOQUEADA (60M){RESET}"
            sinal_db = "BLOQUEIO_H1"
            mensagem = "Correção de baixa dentro de uma tendência de alta (60M subindo). Não venda contra a maré."

    # 3. Lateralidade
    else:
        if term_valor >= 0.5:
            sinal_txt = f"{VERDE}↗️ Viés de Alta Global{RESET}"
            sinal_db = "ALTA"
            mensagem = "Viés leve de alta no exterior, mas não é forte o suficiente para uma entrada agressiva."
        elif term_valor <= -0.5:
            sinal_txt = f"{VERMELHO}↘️ Viés de Baixa Global{RESET}"
            sinal_db = "BAIXA"
            mensagem = "Exterior pesa para baixo. Momento de proteger o capital e evitar compras pesadas."
        else:
            sinal_txt = f"{RESET}⚪ NEUTRO (Sem direção clara){RESET}"
            sinal_db = "NEUTRO"
            mensagem = "Robôs globais brigando sem direção. Mercado lateral e perigoso. Ficar de fora também é operar!"

    return sinal_txt, sinal_db, mensagem