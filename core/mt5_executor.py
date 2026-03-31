import MetaTrader5 as mt5
from core.logger import log

def executar_ordem(simbolo, tipo_sinal, lote, preco_atual, stop_loss_pts, take_profit_pts):
    """
    Envia uma ordem a mercado para o MT5 com Stop Loss e Take Profit calculados.
    tipo_sinal: "COMPRA" ou "VENDA"
    """
    
    # 1. Prepara as variáveis baseadas na direção
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

    # 2. Monta o dicionário da requisição (A Boleta do MT5)
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": simbolo,
        "volume": float(lote),
        "type": ordem_tipo,
        "price": preco_atual,
        "sl": sl,
        "tp": tp,
        "deviation": 10, # Derrapagem máxima (slippage) em pontos
        "magic": 777,    # Número de identificação do nosso Robô
        "comment": "Nemesis Quant",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_RETURN,
    }

    # 3. Dispara a ordem
    log.info(f"[{simbolo}] {acao} {lote} lote(s) no {preco_atual}. SL: {sl} | TP: {tp}")
    resultado = mt5.order_send(request)

    # 4. Auditoria do Resultado
    if resultado.retcode != mt5.TRADE_RETCODE_DONE:
        log.error(f"Falha ao executar ordem: {resultado.comment} (Código: {resultado.retcode})")
        return None
        
    log.info(f"✅ Ordem Executada com Sucesso! Ticket: {resultado.order}")
    
    # Retorna os dados para mandarmos pro Telegram
    return {
        "ticket": resultado.order,
        "preco_executado": resultado.price,
        "sl": sl,
        "tp": tp,
        "lote": lote
    }