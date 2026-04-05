import MetaTrader5 as mt5
from core.logger import log

def gerenciar_trailing_stop(simbolo, gatilho_pts=250, margem_seguranca=100, trailing_step=30):
    """
    Vigia as posições abertas e move o Stop Loss a favor do trade para proteger os lucros.
    
    :param gatilho_pts: Pontos de lucro necessários para ativar a proteção (Breakeven + Trailing).
    :param margem_seguranca: Distância (em pontos) que o SL vai ficar atrás do preço atual.
    :param trailing_step: O SL só se move se for para garantir X pontos a mais (evita spam na corretora).
    """
    posicoes = mt5.positions_get(symbol=simbolo)
    
    # Se não há operações abertas, o robô não gasta processamento
    if posicoes is None or len(posicoes) == 0:
        return

    tick = mt5.symbol_info_tick(simbolo)
    if tick is None:
        return

    for pos in posicoes:
        preco_atual = tick.bid if pos.type == mt5.ORDER_TYPE_BUY else tick.ask
        sl_atual = pos.sl
        tp_atual = pos.tp
        preco_abertura = pos.price_open
        ticket = pos.ticket

        novo_sl = sl_atual
        precisa_atualizar = False

        # =====================================================================
        # GESTÃO DE COMPRA (Trailing Stop Sobe)
        # =====================================================================
        if pos.type == mt5.ORDER_TYPE_BUY:
            lucro_pts = preco_atual - preco_abertura
            
            # 1. Se o preço andou mais que o Gatilho (ex: +250 pontos)
            if lucro_pts >= gatilho_pts:
                sl_calculado = preco_atual - margem_seguranca
                
                # 2. Só movemos o SL se ele for ficar ACIMA do SL antigo + o Step de 30pts
                # Isso impede o robô de mandar 100 requisições por segundo para a B3
                if sl_atual == 0.0 or sl_calculado > (sl_atual + trailing_step):
                    
                    # 3. Trava de Segurança: O SL NUNCA pode ficar abaixo do preço de entrada (Breakeven)
                    if sl_calculado > preco_abertura:
                        novo_sl = sl_calculado
                        precisa_atualizar = True

        # =====================================================================
        # GESTÃO DE VENDA (Trailing Stop Desce)
        # =====================================================================
        elif pos.type == mt5.ORDER_TYPE_SELL:
            lucro_pts = preco_abertura - preco_atual
            
            if lucro_pts >= gatilho_pts:
                sl_calculado = preco_atual + margem_seguranca
                
                if sl_atual == 0.0 or sl_calculado < (sl_atual - trailing_step):
                    if sl_calculado < preco_abertura:
                        novo_sl = sl_calculado
                        precisa_atualizar = True

        # =====================================================================
        # O DISPARO DA ATUALIZAÇÃO (Requisição FIX para a Genial)
        # =====================================================================
        if precisa_atualizar:
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "symbol": simbolo,
                "sl": float(novo_sl),
                "tp": float(tp_atual),
                "position": ticket,
                "magic": 777
            }
            
            resultado = mt5.order_send(request)
            
            if resultado is not None and resultado.retcode == mt5.TRADE_RETCODE_DONE:
                log.info(f"🛡️ TRAILING STOP ACIONADO! Ticket: {ticket} | Lucro na Mesa: +{lucro_pts:.0f} pts | Novo SL Cravado no: {novo_sl}")
            else:
                erro = mt5.last_error() if resultado is None else f"{resultado.comment} (Cod: {resultado.retcode})"
                log.error(f"Falha ao mover Trailing Stop do ticket {ticket}. Erro: {erro}")