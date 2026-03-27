# Cores para o Terminal
VERDE = '\033[92m'
VERMELHO = '\033[91m'
AMARELO = '\033[93m'
AZUL = '\033[96m'
MAGENTA = '\033[95m'
RESET = '\033[0m'

def gerar_relatorio_abertura(fechamento_win_d1, vwap_win_d1, var_sp, var_dxy):
    distancia_fechamento_vwap = fechamento_win_d1 - vwap_win_d1
    
    # Avaliando como o Brasil dormiu
    if distancia_fechamento_vwap > 0:
        contexto_d1 = "COMPRADO (Dormiu acima do preço médio institucional)"
        cor_d1 = VERDE
    else:
        contexto_d1 = "VENDIDO (Dormiu amargando abaixo da VWAP)"
        cor_d1 = VERMELHO

    # Avaliando como o mundo acordou (Humor Global)
    if var_sp > 0.2:
        humor_global = "OTIMISTA (Apetite a risco)"
        cor_humor = VERDE
        peso_gap = 1 # Pressão de Alta
    elif var_sp < -0.2:
        humor_global = "PESSIMISTA (Aversão a risco)"
        cor_humor = VERMELHO
        peso_gap = -1 # Pressão de Baixa
    else:
        humor_global = "NEUTRO (Mercados de lado na madrugada)"
        cor_humor = AMARELO
        peso_gap = 0

    # Adicionando o Dólar (DXY) na balança
    if var_dxy > 0.15: peso_gap -= 1 # Dólar forte puxa índice pra baixo
    elif var_dxy < -0.15: peso_gap += 1 # Dólar fraco ajuda índice

    # Inteligência do Gap
    if peso_gap >= 1:
        vies_gap = f"{VERDE}⬆️ ALTA PROBABILIDADE DE GAP DE ALTA{RESET}"
        if distancia_fechamento_vwap < 0:
            analise = "Os vendidos de ontem estão encurralados. O mundo acordou bem e o índice fechou abaixo da VWAP. Eles terão que zerar posições (comprar), potencializando uma puxada forte na abertura."
        else:
            analise = "O exterior está puxando para cima, ajudando o movimento de quem dormiu comprado ontem. Espere abertura acima da região de fechamento."
            
    elif peso_gap <= -1:
        vies_gap = f"{VERMELHO}⬇️ ALTA PROBABILIDADE DE GAP DE BAIXA{RESET}"
        if distancia_fechamento_vwap > 0:
            analise = "Os comprados de ontem caíram na armadilha. O mundo acordou azedo. Quem dormiu comprado acima da VWAP ontem vai estopar na abertura, acelerando a queda."
        else:
            analise = "Exterior ruim chancelando a força vendedora do dia anterior. O índice deve abrir continuando a maré de baixa de ontem."
            
    else:
        vies_gap = f"{AMARELO}➡️ ABERTURA INDEFINIDA (MISTO){RESET}"
        analise = "Forças conflitantes entre S&P e Dólar, ou variação overnight muito fraca. O índice pode abrir próximo ao fechamento de ontem e ficar lateral nos primeiros minutos. Evite boletar no susto."

    return contexto_d1, cor_d1, humor_global, cor_humor, vies_gap, analise