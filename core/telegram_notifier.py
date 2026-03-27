import requests
import re
from datetime import datetime
from core.logger import log

TOKEN = "8568271144:AAEsglyZGDfOtxbHuEh2joW8J2eI-1V3SKY"
CHAT_ID = "690559715"

# Dicionário para traduzir o código do Banco de Dados para Títulos Premium
TITULOS_SINAIS = {
    "COMPRA": "🟢 COMPRA INSTITUCIONAL CONFIRMADA",
    "VENDA": "🔴 VENDA INSTITUCIONAL CONFIRMADA",
    "BLOQUEIO_VOL": "⚠️ BLOQUEIO: MOVIMENTO SEM VOLUME",
    "BLOQUEIO_VWAP": "⚠️ BLOQUEIO: PREÇO PRESO NA VWAP",
    "BLOQUEIO_H1": "⚠️ BLOQUEIO: CONTRA A MARÉ",
    "BLOQUEIO_ELASTICO": "🛑 PERIGO: EFEITO ELÁSTICO (ESTICADO)",
    "DESCOLAMENTO_MACRO": "🚨 ANOMALIA: BRASIL DESCOLADO",
    "NEUTRO_CAIXOTE": "💤 MERCADO PRESO (CAIXOTE NA POC)",
    "ALTA": "↗️ VIÉS LEVE DE ALTA (AGUARDE)",
    "BAIXA": "↘️ VIÉS LEVE DE BAIXA (AGUARDE)",
    "NEUTRO": "⚪ MERCADO NEUTRO (BRIGA DE ROBÔS)"
}

def limpar_ansi(texto):
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', texto)

def notificar_telegram(tipo_alerta, sinal_db, mensagem_bruta, preco, termometro, dist_vwap, tem_volume, tendencia_60m, atr, poc):
    mensagem_limpa = limpar_ansi(mensagem_bruta)
    hora = datetime.now().strftime("%H:%M")
    
    # Define o título principal
    titulo_formatado = TITULOS_SINAIS.get(sinal_db, f"SINAL: {sinal_db}")
    if tipo_alerta == "ALERTA MACRO":
        titulo_formatado = "📰 ALERTA DE CALENDÁRIO MACRO"
    elif "VALIDAÇÃO" in tipo_alerta:
        titulo_formatado = f"🔎 RAIO-X MANUAL: {TITULOS_SINAIS.get(sinal_db, sinal_db)}"

    # Status textuais
    status_vol = "✅ Forte (Acima da Média)" if tem_volume else "❌ Oco (Sem Dinheiro)"
    icone_term = "🔥" if termometro > 0 else "🧊"
    
    texto_telegram = (
        f"<b>{titulo_formatado}</b>\n"
        f"🕒 <i>Ref: {hora}</i>\n\n"
        f"📊 <b>MÉTRICAS DO PREGÃO:</b>\n"
        f"• <b>WIN Atual:</b> <code>{preco:.0f}</code>\n"
        f"• <b>Termômetro:</b> <code>{termometro:+.2f} {icone_term}</code>\n"
        f"• <b>Dist. VWAP:</b> <code>{dist_vwap:+.0f} pts</code>\n"
        f"• <b>Fluxo de Lote:</b> <i>{status_vol}</i>\n"
        f"• <b>Tendência 60M:</b> <i>{tendencia_60m}</i>\n"
        f"• <b>Volatilidade (ATR):</b> <code>{atr:.0f} pts</code>\n"
        f"• <b>Alvo POC:</b> <code>{poc:.0f}</code>\n"
        f"---------------------------\n"
        f"💡 <b>VOZ SUPREMA:</b>\n{mensagem_limpa}"
    )

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": texto_telegram,
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=5)
        if response.status_code == 200:
            log.info(f"Notificação Telegram enviada: {sinal_db}")
        else:
            log.error(f"Erro Telegram: {response.text}")
    except Exception as e:
        log.error(f"Falha de conexão com Telegram: {e}")