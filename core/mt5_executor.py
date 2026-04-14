import MetaTrader5 as mt5
from typing import Optional, Tuple
from core.logger import log
from core.config import cfg
from core.models import OrderResult

def executar_ordem(simbolo: str, tipo_sinal: str, lote: float, preco_atual: float, stop_loss_pts: float, take_profit_pts: float) -> Optional[OrderResult]:
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
        "magic": cfg.MAGIC_NUMBER,
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
    
    return OrderResult(
        ticket=resultado.order,
        preco_executado=resultado.price,
        sl=sl,
        tp=tp,
        lote=lote
    )

def zerar_posicoes(simbolo: str) -> Tuple[bool, str]:
    """
    Escaneia a conta em busca de posições abertas no ativo e executa a 
    liquidação a mercado (Zeragem Compulsória).
    """
    posicoes = mt5.positions_get(symbol=simbolo)
    
    if posicoes is None or len(posicoes) == 0:
        return True, "Nenhuma posição em aberto."
        
    sucesso_total = True
    
    for pos in posicoes:
        # Se está comprado, o tipo para fechar é Venda. Se está vendido, é Compra.
        tipo_fechamento = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
        acao = "Vendendo" if tipo_fechamento == mt5.ORDER_TYPE_SELL else "Comprando"
        
        # Puxa o tick atual para mandar a mercado
        tick = mt5.symbol_info_tick(simbolo)
        preco_mercado = tick.bid if tipo_fechamento == mt5.ORDER_TYPE_SELL else tick.ask
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": simbolo,
            "volume": float(pos.volume),
            "type": tipo_fechamento,
            "position": pos.ticket, # <--- O SEGREDO: Referencia o ticket da ordem que está aberta
            "price": float(preco_mercado),
            "deviation": 20, # Derrapagem maior permitida por ser zeragem de segurança
            "magic": cfg.MAGIC_NUMBER,
            "comment": "Zeragem Compulsoria",
            "type_time": mt5.ORDER_TIME_DAY,
            "type_filling": mt5.ORDER_FILLING_RETURN,
        }
        
        log.warning(f"🚨 INICIANDO ZERAGEM: {acao} {pos.volume} lotes de {simbolo} a mercado para fechar ticket {pos.ticket}!")
        
        resultado = mt5.order_send(request)
        
        if resultado is None or resultado.retcode != mt5.TRADE_RETCODE_DONE:
            erro = mt5.last_error() if resultado is None else f"{resultado.comment} ({resultado.retcode})"
            log.error(f"FALHA CRÍTICA na zeragem do ticket {pos.ticket}. Erro: {erro}")
            sucesso_total = False
        else:
            log.info(f"✅ Liquidação Concluída! Ticket {pos.ticket} encerrado com sucesso.")
            
    return sucesso_total, "Protocolo de liquidação executado."