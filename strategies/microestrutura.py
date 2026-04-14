import pandas as pd
from core.footprint import ler_fita_m1
from core.dom_reader import escanear_muralhas_book
from core.models import FlowAnalysisResult, SequentialValidationResult

def analisar_fluxo_m1(simbolo: str, df_m1: pd.DataFrame, direcao_macro: str) -> FlowAnalysisResult:
    """
    O Sniper: Cruza Absorção (Cracudo), Exaustão, Saldo Delta (Tape Reading) e DOM (Book).
    """
    if df_m1 is None or len(df_m1) < 10:
        return FlowAnalysisResult(False, "Dados insuficientes no M1")

    vela_atual = df_m1.iloc[-2]
    vol_1 = df_m1['real_volume'].iloc[-2]
    vol_2 = df_m1['real_volume'].iloc[-3]
    vol_3 = df_m1['real_volume'].iloc[-4]
    
    media_vol = df_m1['real_volume'].tail(10).mean()
    tamanho_vela = vela_atual['high'] - vela_atual['low']
    preco_fechamento = vela_atual['close']
    
    if tamanho_vela == 0:
        return False, "Vela sem amplitude"

    corpo_vela = abs(vela_atual['open'] - preco_fechamento)
    
    # 1. Leitura da Fita Executada (Footprint)
    fita = ler_fita_m1(simbolo)
    saldo_delta = fita['saldo_delta'] if fita else 0

    # 2. Leitura da Profundidade Institucional (DOM)
    # Procuramos escoras de no mínimo 500 contratos (Tubaroes)
    dom = escanear_muralhas_book(simbolo, lote_minimo_institucional=500)
    muralha_compra = dom['muralha_compra_preco'] if dom else None
    muralha_venda = dom['muralha_venda_preco'] if dom else None

    # =========================================================================
    # BLOQUEIOS ANTI-ARMADILHA
    # =========================================================================
    if corpo_vela > 150 and vol_1 < media_vol and abs(saldo_delta) < (media_vol * 0.1):
        return FlowAnalysisResult(False, f"BLOQUEIO: Vela oca (Delta: {saldo_delta}).")

    # Se a estratégia mandar COMPRAR, mas o preço está espremido exatamente abaixo de uma MURALHA DE VENDA
    if direcao_macro == "COMPRA" and muralha_venda is not None:
        distancia_resistencia = muralha_venda - preco_fechamento
        if 0 < distancia_resistencia < 50: # Se a muralha está a menos de 50 pontos acima
            return FlowAnalysisResult(False, f"BLOQUEIO DOM: Muralha vendedora detectada em {muralha_venda} ({dom['muralha_venda_vol']} contratos).")

    # Se a estratégia mandar VENDER, mas o preço está amassado em cima de uma MURALHA DE COMPRA
    if direcao_macro == "VENDA" and muralha_compra is not None:
        distancia_suporte = preco_fechamento - muralha_compra
        if 0 < distancia_suporte < 50: # Se a muralha está a menos de 50 pontos abaixo
            return FlowAnalysisResult(False, f"BLOQUEIO DOM: Muralha compradora detectada em {muralha_compra} ({dom['muralha_compra_vol']} contratos).")

    # =========================================================================
    # IDENTIFICAÇÃO DE EXAUSTÃO
    # =========================================================================
    exaustao_confirmada = (vol_3 > vol_2 > vol_1) and (vol_1 < media_vol)

    # =========================================================================
    # GATILHOS FURA-FILA (Ataque de Sniper)
    # =========================================================================
    if direcao_macro == "COMPRA":
        menor_corpo = min(vela_atual['open'], preco_fechamento)
        tamanho_pavio_inf = menor_corpo - vela_atual['low']
        
        if (tamanho_pavio_inf / tamanho_vela) >= 0.60 and vol_1 > media_vol:
            msg_extra = f" Apoiado por Muralha no {muralha_compra}!" if muralha_compra and (preco_fechamento - muralha_compra < 150) else ""
            if saldo_delta < 0:
                return FlowAnalysisResult(True, f"FURA-FILA: Absorção Perfeita. Bateram {abs(saldo_delta)}, lote passivo segurou.{msg_extra}")
            else:
                return FlowAnalysisResult(True, f"FURA-FILA: Rejeição compradora (Delta: +{saldo_delta}).{msg_extra}")
                
        if exaustao_confirmada and preco_fechamento >= vela_atual['open']:
            return FlowAnalysisResult(True, "FURA-FILA: Exaustão confirmada. Secou o lote vendedor.")

    elif direcao_macro == "VENDA":
        maior_corpo = max(vela_atual['open'], preco_fechamento)
        tamanho_pavio_sup = vela_atual['high'] - maior_corpo
        
        if (tamanho_pavio_sup / tamanho_vela) >= 0.60 and vol_1 > media_vol:
            msg_extra = f" Apoiado por Muralha no {muralha_venda}!" if muralha_venda and (muralha_venda - preco_fechamento < 150) else ""
            if saldo_delta > 0:
                return FlowAnalysisResult(True, f"FURA-FILA: Absorção Perfeita. Tomaram {saldo_delta}, lote passivo travou.{msg_extra}")
            else:
                return FlowAnalysisResult(True, f"FURA-FILA: Rejeição vendedora (Delta: {saldo_delta}).{msg_extra}")
                
        if exaustao_confirmada and preco_fechamento <= vela_atual['open']:
            return FlowAnalysisResult(True, "FURA-FILA: Exaustão confirmada. Secou o lote comprador.")

    return FlowAnalysisResult(False, "Fluxo do M1 dentro da normalidade.")

# =========================================================================
# CONFIRMAÇÃO DE SEQUENCIAL INSTITUCIONAL (VWAP/TWAP)
# =========================================================================

def confirmar_sequencial(simbolo: str, tipo_posicao_aberta: str) -> SequentialValidationResult:
    """
    Escaneia a fita em busca do Algoritmo VWAP/TWAP institucional (Progressão/Sequencial).
    Se o robô do banco começar a tomar/bater lote a mercado a nosso favor, confirmamos o Scale-In.
    """
    fita = ler_fita_m1(simbolo)
    if not fita:
        return SequentialValidationResult(False, "Aguardando fita...")

    saldo_delta = fita['saldo_delta']

    # O 'Trigger' de Sequencial Institucional (Agressão massiva no último minuto)
    # Parametrizado para 250 contratos de saldo líquido a favor
    DELTA_GATILHO = 250

    if tipo_posicao_aberta == "COMPRA":
        if saldo_delta >= DELTA_GATILHO:
            return SequentialValidationResult(True, f"🌊 Sequencial Confirmado! Robôs tomando a mercado (Delta: +{saldo_delta}).")
            
    elif tipo_posicao_aberta == "VENDA":
        if saldo_delta <= -DELTA_GATILHO:
            return SequentialValidationResult(True, f"🌊 Sequencial Confirmado! Robôs batendo a mercado (Delta: {saldo_delta}).")

    return SequentialValidationResult(False, f"Aguardando tração do fluxo (Delta atual: {saldo_delta})")