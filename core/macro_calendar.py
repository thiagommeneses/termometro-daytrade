from datetime import datetime

# Dossiê Quantitativo dos maiores eventos macroeconômicos do mercado
EVENTOS_MACRO = {
    "10:30": {
        "nome": "Abertura NYSE / Dados EUA (Payroll/CPI)",
        "perfil_historico": "Explosão de liquidez. Robôs de Alta Frequência (HFT) caçam stops nos primeiros 3 minutos. O WIN costuma espelhar o S&P 500 com violência. Se o Dólar (DXY) estourar para um lado, opere o WIN para o lado oposto sem hesitar. Ignore pequenos repiques na VWAP.",
        "ajuste_risco": "Aumentar Stop Loss para 2x o ATR. Reduzir tamanho da mão (lote) pela metade."
    },
    "15:00": {
        "nome": "Decisão de Juros FED / FOMC",
        "perfil_historico": "Risco de 'Violinada Dupla'. O mercado costuma dar um falso rompimento agressivo para um lado nos primeiros minutos, estopa todo mundo, e depois toma a tendência real guiada pelo S&P 500.",
        "ajuste_risco": "Stop Loss de proteção máxima (3x ATR). Ficar de fora nos primeiros 5 minutos é a melhor posição."
    },
    "09:00": {
        "nome": "Abertura Mercado à Vista (Brasil) / Leilão",
        "perfil_historico": "Ajuste de posições locais. Volume financeiro aumenta drasticamente. O preço tende a buscar a VWAP do dia anterior antes de definir a tendência do dia.",
        "ajuste_risco": "Atenção ao Gap. Operar a favor do fechamento do Gap se o S&P 500 apoiar."
    }
}

def verificar_alerta_macro(hora_atual_str=None):
    """
    Verifica se estamos na janela de 15 minutos antes ou depois de um evento macro.
    Não bloqueia a operação, apenas fornece o Dossiê Histórico e Ajuste de Risco.
    """
    if hora_atual_str is None:
        hora_atual_str = datetime.now().strftime("%H:%M")
        
    formato = "%H:%M"
    agora = datetime.strptime(hora_atual_str[:5], formato)
    
    for hora_evento, dados in EVENTOS_MACRO.items():
        evento_time = datetime.strptime(hora_evento, formato)
        
        # Calcula a diferença em minutos
        diff_minutos = (agora - evento_time).total_seconds() / 60.0
        
        # Janela de perigo: 15 minutos antes até 15 minutos depois do evento
        if -15 <= diff_minutos <= 15:
            minutos_txt = f"Faltam {abs(int(diff_minutos))} min" if diff_minutos < 0 else f"Passaram {int(diff_minutos)} min"
            if diff_minutos == 0: minutos_txt = "AGORA!"
            
            alerta = (
                f"🚨 ALERTA MACRO [{minutos_txt}]: {dados['nome']}\n"
                f"   📚 Histórico: {dados['perfil_historico']}\n"
                f"   🛡️ Risco Sugerido: {dados['ajuste_risco']}"
            )
            return alerta
            
    return None # Nenhum evento no radar