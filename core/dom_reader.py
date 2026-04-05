import MetaTrader5 as mt5
import pandas as pd
from core.logger import log

def escanear_muralhas_book(simbolo, lote_minimo_institucional=500):
    """
    Assina e lê o Depth of Market (DOM) em tempo real.
    Procura por 'Escoras' (Muralhas de Lotes) penduradas no Book de Ofertas.
    
    :param lote_minimo_institucional: Volume mínimo em um único nível de preço para ser considerado uma Muralha.
    """
    # Garante que o Python está inscrito para receber os dados do Book Nível 3
    mt5.market_book_add(simbolo)
    
    # Puxa a fotografia exata do Book neste milissegundo
    book = mt5.market_book_get(simbolo)
    
    if book is None or len(book) == 0:
        return None
        
    # Converte os dados brutos de C++ para um DataFrame legível
    df_book = pd.DataFrame(list(book), columns=book[0]._asdict().keys())
    
    # Filtra o book: type 1 = Venda (Asks/Resistência), type 2 = Compra (Bids/Suporte)
    vendas = df_book[df_book['type'] == mt5.BOOK_TYPE_SELL].copy()
    compras = df_book[df_book['type'] == mt5.BOOK_TYPE_BUY].copy()
    
    muralha_venda = None
    muralha_compra = None
    
    # 1. Escaneia o Book Vendedor (Procurando Teto de Concreto)
    if not vendas.empty:
        # Filtra apenas os níveis de preço que têm lote maior que o mínimo institucional
        vendas_fortes = vendas[vendas['volume'] >= lote_minimo_institucional]
        if not vendas_fortes.empty:
            # Pega a muralha que está mais PRÓXIMA do preço atual (menor preço de venda)
            muralha_venda = vendas_fortes.sort_values(by='price', ascending=True).iloc[0]
            
    # 2. Escaneia o Book Comprador (Procurando Piso de Concreto)
    if not compras.empty:
        compras_fortes = compras[compras['volume'] >= lote_minimo_institucional]
        if not compras_fortes.empty:
            # Pega a muralha que está mais PRÓXIMA do preço atual (maior preço de compra)
            muralha_compra = compras_fortes.sort_values(by='price', ascending=False).iloc[0]

    return {
        "muralha_venda_preco": float(muralha_venda['price']) if muralha_venda is not None else None,
        "muralha_venda_vol": float(muralha_venda['volume']) if muralha_venda is not None else 0,
        "muralha_compra_preco": float(muralha_compra['price']) if muralha_compra is not None else None,
        "muralha_compra_vol": float(muralha_compra['volume']) if muralha_compra is not None else 0
    }