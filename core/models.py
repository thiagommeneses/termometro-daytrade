from dataclasses import dataclass
from typing import Optional

@dataclass
class MarketContext:
    termometro: float
    tendencia_sp: str
    tendencia_win: str
    fechamento_win: float
    vwap_atual: float
    tem_volume: bool
    distancia_vwap: float
    poc_atual: float
    atr_atual: float
    correlacao: float
    alerta_macro: Optional[str] = None

@dataclass
class AnalysisResult:
    sinal_txt: str
    sinal_db: str
    mensagem: str

@dataclass
class OrderResult:
    ticket: int
    preco_executado: float
    sl: float
    tp: float
    lote: float

@dataclass
class FlowAnalysisResult:
    aprovado: bool
    mensagem: str

@dataclass
class SequentialValidationResult:
    confirmado: bool
    mensagem: str
