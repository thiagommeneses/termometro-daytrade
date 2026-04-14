# ==============================================================================
# CONFIGURAÇÃO CENTRAL DO SISTEMA (Lê do .env)
# ==============================================================================
# Importar 'from core.config import cfg' em qualquer módulo para acessar.
# Trocar o contrato? Edite APENAS o arquivo .env na raiz do projeto.
# ==============================================================================

import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega o .env da raiz do projeto (sobe um nível a partir de /core/)
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)

class _Config:
    """Objeto de configuração que lê do .env com fallbacks seguros."""

    # Tickers
    TICKER_WIN: str = os.getenv("TICKER_WIN", "WINM26")
    TICKER_VIX: str = os.getenv("TICKER_VIX", "VIX")
    TICKER_DXY: str = os.getenv("TICKER_DXY", "USDX")
    TICKER_SP:  str = os.getenv("TICKER_SP", "US500")

    # Caminhos dos Terminais MT5
    MT5_PATH_GENIAL: str = os.getenv("MT5_PATH_GENIAL", r"C:\Program Files\MetaTrader 5\terminal64.exe")
    MT5_PATH_ZERO:   str = os.getenv("MT5_PATH_ZERO", r"C:\Program Files\Zero Financial MT5 Terminal\terminal64.exe")

    # Telegram
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID:   str = os.getenv("TELEGRAM_CHAT_ID", "")

    # Execução
    MAGIC_NUMBER: int = int(os.getenv("MAGIC_NUMBER", "777"))

    # Banco de Dados
    DB_NAME: str = os.getenv("DB_NAME", "dados_mercado.db")

# Instância global — importe assim: from core.config import cfg
cfg = _Config()
