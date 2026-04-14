import requests
import re
from datetime import datetime
from core.logger import log
from core.config import cfg

TOKEN = cfg.TELEGRAM_BOT_TOKEN
CHAT_ID = cfg.TELEGRAM_CHAT_ID

# Dicionário para traduzir o código do Banco de Dados para Títulos Premium
TITULOS_SINAIS = {
    "COMPRA": "🟢 COMPRA INSTITUCIONAL CONFIRMADA",
    "VENDA": "🔴 VENDA INSTITUCIONAL CONFIRMADA",
    "BLOQUEIO_VOL": "⚠️ BLOQUEIO: MOVIMENTO SEM VOLUME",
    "BLOQUEIO_VWAP": "⚠️ BLOQUEIO: PREÇO PRESO NA VWAP",
    "BLOQUEIO_H1": "⚠️ BLOQUEIO: CONTRA A MARÉ",
    "BLOQUEIO_ELASTICO": "🛑 PERIGO: EFEITO ELÁSTICO (ESTICADO) - [Risco de Retorno à Média]",
    "DESCOLAMENTO_MACRO": "🚨 ANOMALIA: BRASIL DESCOLADO",
    "NEUTRO_CAIXOTE": "💤 MERCADO PRESO (CAIXOTE NA POC)",
    "ALTA": "↗️ VIÉS LEVE DE ALTA (AGUARDE)",
    "BAIXA": "↘️ VIÉS LEVE DE BAIXA (AGUARDE)",
    "NEUTRO": "⚪ MERCADO NEUTRO (BRIGA DE ROBÔS)"
}

# Função para limpar códigos ANSI (cores e formatações) das mensagens antes de enviar para o Telegram, garantindo que o texto fique legível e sem caracteres estranhos. O Telegram não interpreta códigos ANSI, então é importante remover esses códigos para evitar mensagens confusas. Essa função utiliza uma expressão regular para identificar e eliminar os códigos ANSI presentes na mensagem bruta, resultando em um texto limpo e pronto para ser enviado ao Telegram.
def limpar_ansi(texto: str) -> str:
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', texto)

# Notificação principal para sinais e alertas, com foco em métricas de mercado e insights detalhados
def notificar_telegram(tipo_alerta: str, sinal_db: str, mensagem_bruta: str, preco: float, termometro: float, dist_vwap: float, tem_volume: bool, tendencia_60m: str, atr: float, poc: float) -> None:
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
        
        
# Notificação específica para ordens executadas, com foco na ação e detalhes da operação
# Essa função é chamada após a execução bem-sucedida de uma ordem, para informar rapidamente sobre a operação realizada.

def notificar_execucao(acao: str, simbolo: str, preco: float, lote: float, sl: float, tp: float, motivo: str = "Alinhamento Institucional") -> None:
    """Envia notificação curta focada apenas na execução da ordem"""
    hora = datetime.now().strftime("%H:%M:%S")
    icone = "🟢" if acao == "COMPRA" else "🔴"
    
    texto_telegram = (
        f"<b>{icone} ORDEM EXECUTADA (AUTO-TRADING)</b>\n"
        f"🕒 <i>{hora}</i>\n\n"
        f"• <b>Ativo:</b> {simbolo}\n"
        f"• <b>Ação:</b> {acao} ({lote} lote)\n"
        f"• <b>Preço:</b> <code>{preco:.0f}</code>\n"
        f"• <b>Stop Loss:</b> <code>{sl:.0f}</code>\n"
        f"• <b>Take Profit:</b> <code>{tp:.0f}</code>\n"
        f"• <b>Motivo:</b> <i>{motivo}</i>"
    )

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": texto_telegram,
        "parse_mode": "HTML"
    }
    
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        log.error(f"Falha ao enviar notificação de execução: {e}")