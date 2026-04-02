def cacador_de_absorcao(df_m1, direcao_macro):
    """
    Analisa os últimos candles de 1 Minuto (M1) em busca de padrões de rejeição/absorção 
    (O famoso "craquezinho" do Vitão) alinhados com o direcional Macro.
    """
    if df_m1 is None or len(df_m1) < 10:
        return False, "Dados insuficientes no M1"

    # Pega a última vela fechada do M1 (a penúltima do dataframe, já que a última ainda está se movendo)
    vela_sinal = df_m1.iloc[-2]
    
    abertura = vela_sinal['open']
    fechamento = vela_sinal['close']
    maxima = vela_sinal['high']
    minima = vela_sinal['low']
    volume_atual = vela_sinal['real_volume']
    
    # Calcula a média de volume das últimas 10 velas do M1
    media_vol_m1 = df_m1['real_volume'].tail(10).mean()
    
    tamanho_total = maxima - minima
    if tamanho_total == 0:
        return False, "Vela sem amplitude"

    # =========================================================================
    # CENÁRIO 1: CAÇANDO FUNDOS (Sinal de COMPRA)
    # =========================================================================
    if direcao_macro == "COMPRA":
        # O corpo da vela (onde abriu/fechou)
        menor_corpo = min(abertura, fechamento)
        tamanho_pavio_inferior = menor_corpo - minima
        
        # Regra: Pavio inferior tem que ser pelo menos 60% da vela E volume acima da média
        if (tamanho_pavio_inferior / tamanho_total) >= 0.60 and volume_atual > media_vol_m1:
            return True, "ABSORÇÃO NO FUNDO (M1): Forte pavio de rejeição com volume."

    # =========================================================================
    # CENÁRIO 2: CAÇANDO TOPOS (Sinal de VENDA)
    # =========================================================================
    elif direcao_macro == "VENDA":
        maior_corpo = max(abertura, fechamento)
        tamanho_pavio_superior = maxima - maior_corpo
        
        # Regra: Pavio superior tem que ser pelo menos 60% da vela E volume acima da média
        if (tamanho_pavio_superior / tamanho_total) >= 0.60 and volume_atual > media_vol_m1:
            return True, "ABSORÇÃO NO TOPO (M1): Forte pavio de rejeição com volume."

    return False, "Nenhum padrão de absorção encontrado no M1."