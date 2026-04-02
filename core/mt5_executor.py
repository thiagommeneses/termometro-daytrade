import MetaTrader5 as mt5
from core.logger import log

def executar_ordem(simbolo, tipo_sinal, lote, preco_atual, stop_loss_pts, take_profit_pts):
    """
    Envia uma ordem a mercado para o MT5 com Stop Loss e Take Profit calculados.
    Válido apenas para o pregão atual (ORDER_TIME_DAY).
    """
    
    # 1. BLINDAGEM OBRIGATÓRIA (Casting): 
    # Converte os tipos numpy.float64 do Pandas para float nativo do Python
    preco_atual = float(preco_atual)
    stop_loss_pts = float(stop_loss_pts)
    take_profit_pts = float(take_profit_pts)
    lote = float(lote)

    # 2. Prepara as variáveis baseadas na direção
    if tipo_sinal == "COMPRA":
        ordem_tipo = mt5.ORDER_TYPE_BUY
        sl = preco_atual - stop_loss_pts
        tp = preco_atual + take_profit_pts
        acao = "Comprando"
    elif tipo_sinal == "VENDA":
        ordem_tipo = mt5.ORDER_TYPE_SELL
        sl = preco_atual + stop_loss_pts
        tp = preco_atual - take_profit_pts
        acao = "Vendendo"
    else:
        log.warning(f"Sinal inválido para execução: {tipo_sinal}")
        return None

    # 3. Monta o dicionário da requisição (A Boleta do MT5)
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": simbolo,
        "volume": lote,
        "type": ordem_tipo,
        "price": preco_atual,
        "sl": sl,
        "tp": tp,
        "deviation": 10, 
        "magic": 777,    
        "comment": "Nemesis Quant",
        "type_time": mt5.ORDER_TIME_DAY, # <--- CORREÇÃO APLICADA AQUI (Validade Diária)
        "type_filling": mt5.ORDER_FILLING_RETURN,
    }

    log.info(f"[{simbolo}] {acao} {lote} lote(s) no {preco_atual}. SL: {sl} | TP: {tp}")
    
    # 4. O Disparo
    resultado = mt5.order_send(request)

    # 5. BLINDAGEM CONTRA CRASH
    if resultado is None:
        erro = mt5.last_error()
        log.error(f"CRÍTICO: MT5 rejeitou a ordem e retornou None. Código de erro MT5: {erro}")
        return None

    # 6. Auditoria do Resultado da Corretora
    if resultado.retcode != mt5.TRADE_RETCODE_DONE:
        log.error(f"Falha ao executar ordem na Genial: {resultado.comment} (Código: {resultado.retcode})")
        return None
        
    log.info(f"✅ Ordem Executada com Sucesso! Ticket: {resultado.order}")
    
    return {
        "ticket": resultado.order,
        "preco_executado": resultado.price,
        "sl": sl,
        "tp": tp,
        "lote": lote
    }