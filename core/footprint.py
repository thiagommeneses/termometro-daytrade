import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta

def ler_fita_m1(simbolo):
    """
    Lê a fita de negócios (Tick a Tick) do último minuto fechado.
    Calcula o Saldo Delta (Agressão Compra - Agressão Venda) e procura Sequenciais.
    """
    agora = datetime.now()
    um_minuto_atras = agora - timedelta(minutes=1)
    
    # Puxa todos os negócios (trades) executados na fita no último minuto
    ticks = mt5.copy_ticks_range(simbolo, um_minuto_atras, agora, mt5.COPY_TICKS_TRADE)
    
    if ticks is None or len(ticks) == 0:
        return None
        
    df_ticks = pd.DataFrame(ticks)
    
    # Inicializa os contadores institucionais
    agressao_compra = 0
    agressao_venda = 0
    
    # O MT5 usa 'flags' binárias para dizer quem agrediu o book
    TICK_FLAG_BUY = 32   # Agressor tomou a mercado (Compra)
    TICK_FLAG_SELL = 64  # Agressor bateu a mercado (Venda)
    
    for _, negocio in df_ticks.iterrows():
        flags = negocio['flags']
        volume_contratos = negocio['volume']
        
        # Filtra quem foi o agressor do negócio
        if (flags & TICK_FLAG_BUY):
            agressao_compra += volume_contratos
        elif (flags & TICK_FLAG_SELL):
            agressao_venda += volume_contratos

    # A Mágica do Módulo 6: Saldo Delta
    saldo_delta = agressao_compra - agressao_venda
    volume_total = agressao_compra + agressao_venda
    
    # Calcula se há um desbalanceamento massivo (ex: Delta é mais de 40% do volume total)
    forca_direcional = 0
    if volume_total > 0:
        forca_direcional = (abs(saldo_delta) / volume_total) * 100

    return {
        "agressao_compra": agressao_compra,
        "agressao_venda": agressao_venda,
        "saldo_delta": saldo_delta,
        "volume_total": volume_total,
        "forca_direcional": forca_direcional
    }