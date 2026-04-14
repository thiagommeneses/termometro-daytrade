import MetaTrader5 as mt5
from core.config import cfg

def testar_conexao():
    if not mt5.initialize():
        print("❌ Falha ao inicializar o MetaTrader 5.")
        return
        
    simbolo = cfg.TICKER_WIN
    
    # NOVO: Força o MT5 a 'enxergar' e ativar o ativo no Market Watch
    if not mt5.symbol_select(simbolo, True):
        print(f"❌ Erro: Não foi possível ativar o ativo {simbolo} no MT5.")
        mt5.shutdown()
        return
        
    tick = mt5.symbol_info_tick(simbolo)
    
    if tick is None:
        print(f"❌ Erro: O MT5 ativou o ativo, mas não conseguiu puxar o preço atual de {simbolo}.")
        mt5.shutdown()
        return
        
    # Coloca a ordem 1.000 pontos ABAIXO do preço atual (Impossível de executar agora)
    preco_longe = float(tick.ask - 1000) 
    
    request = {
        "action": mt5.TRADE_ACTION_PENDING,
        "symbol": simbolo,
        "volume": 1.0,
        "type": mt5.ORDER_TYPE_BUY_LIMIT,
        "price": preco_longe,
        "magic": cfg.MAGIC_NUMBER,
        "comment": "Ping Test IPC",
        # "type_time": mt5.ORDER_TIME_GTC,
        "type_time": mt5.ORDER_TIME_DAY,  # Ordem válida apenas para o dia, para evitar surpresas no dia seguinte
        "type_filling": mt5.ORDER_FILLING_RETURN,
    }
    
    print(f"🚀 Disparando ordem de teste: BUY LIMIT 1.0 {simbolo} @ {preco_longe}")
    resultado = mt5.order_send(request)
    
    if resultado is None:
        print(f"❌ ERRO IPC MT5: A API rejeitou o comando. Erro: {mt5.last_error()}")
    elif resultado.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"❌ ERRO CORRETORA: {resultado.comment} (Código: {resultado.retcode})")
    else:
        print(f"✅ SUCESSO ABSOLUTO! Conexão IPC perfeita. Ticket gerado: {resultado.order}")
        print("👉 Vá no seu MT5 agora e apenas clique no 'X' para cancelar a ordem pendente no gráfico.")
        
    mt5.shutdown()

if __name__ == "__main__":
    testar_conexao()