from core.footprint import ler_fita_m1

def analisar_fluxo_m1(simbolo, df_m1, direcao_macro):
    """
    Analisa o fluxo de 1 Minuto cruzando: Absorção (Cracudo), Exaustão e Saldo Delta.
    """
    if df_m1 is None or len(df_m1) < 10:
        return False, "Dados insuficientes no M1"

    vela_atual = df_m1.iloc[-2]
    vol_1 = df_m1['real_volume'].iloc[-2]
    vol_2 = df_m1['real_volume'].iloc[-3]
    vol_3 = df_m1['real_volume'].iloc[-4]
    
    media_vol = df_m1['real_volume'].tail(10).mean()
    tamanho_vela = vela_atual['high'] - vela_atual['low']
    
    if tamanho_vela == 0:
        return False, "Vela sem amplitude"

    corpo_vela = abs(vela_atual['open'] - vela_atual['close'])
    
    # Leitura da Fita em Tempo Real (Tick a Tick)
    fita = ler_fita_m1(simbolo)
    saldo_delta = fita['saldo_delta'] if fita else 0
    forca_direcional = fita['forca_direcional'] if fita else 0

    # =========================================================================
    # 1. FILTRO ANTI-ARMADILHA (Agressão Oca)
    # =========================================================================
    if corpo_vela > 150 and vol_1 < media_vol and abs(saldo_delta) < (media_vol * 0.1):
        return False, f"BLOQUEIO: Vela gigante sem saldo institucional (Delta Oco: {saldo_delta})."

    # =========================================================================
    # 2. IDENTIFICAÇÃO DE EXAUSTÃO (A Seca do Lote)
    # =========================================================================
    exaustao_confirmada = (vol_3 > vol_2 > vol_1) and (vol_1 < media_vol)

    # =========================================================================
    # 3. GATILHOS DE COMPRA (Caçando Fundo)
    # =========================================================================
    if direcao_macro == "COMPRA":
        menor_corpo = min(vela_atual['open'], vela_atual['close'])
        tamanho_pavio_inf = menor_corpo - vela_atual['low']
        
        if (tamanho_pavio_inf / tamanho_vela) >= 0.60 and vol_1 > media_vol:
            if saldo_delta < 0:
                return True, f"FURA-FILA: Absorção perfeita. Bateram {abs(saldo_delta)} na venda, mas o lote passivo segurou."
            else:
                return True, f"FURA-FILA: Rejeição com força compradora (Delta: +{saldo_delta})."
                
        if exaustao_confirmada and vela_atual['close'] >= vela_atual['open']:
            return True, "FURA-FILA: Exaustão da venda confirmada. Vendedor perdeu o lote."

    # =========================================================================
    # 4. GATILHOS DE VENDA (Caçando Topo)
    # =========================================================================
    elif direcao_macro == "VENDA":
        maior_corpo = max(vela_atual['open'], vela_atual['close'])
        tamanho_pavio_sup = vela_atual['high'] - maior_corpo
        
        if (tamanho_pavio_sup / tamanho_vela) >= 0.60 and vol_1 > media_vol:
            if saldo_delta > 0:
                return True, f"FURA-FILA: Absorção perfeita. Tomaram {saldo_delta} na compra, mas o lote passivo travou o preço."
            else:
                return True, f"FURA-FILA: Rejeição com força vendedora (Delta: {saldo_delta})."
                
        if exaustao_confirmada and vela_atual['close'] <= vela_atual['open']:
            return True, "FURA-FILA: Exaustão da compra confirmada. Comprador perdeu o lote."

    return False, "Fluxo do M1 dentro da normalidade."