# 🌅 Relatório de Pré-Mercado — Análise do Leilão WIN

## O que é isso?

O `leilao.py` é uma ferramenta de análise de **pré-mercado** para o minicontrato de índice (WIN). Antes da abertura do pregão (09:00), ele coleta dados do MetaTrader 5 e gera um relatório resumido no terminal com três informações essenciais:

1. **O espelho de ontem (D-1):** como o índice brasileiro fechou em relação ao preço médio institucional (VWAP). Isso indica se o mercado "dormiu" com posições compradas ou vendidas.
2. **O humor global overnight:** variação do S&P 500 Futuro e do Índice Dólar (DXY) durante a madrugada, revelando o apetite de risco internacional.
3. **Projeção do leilão:** com base nos dados acima, o script estima se a abertura terá viés de **alta**, **baixa** ou ficará **indefinida**, junto com uma análise explicativa do cenário.

---

## Pré-requisitos

- **Python 3.10+** instalado
- **MetaTrader 5** instalado no computador, com **dois terminais configurados**:
  - Terminal **Genial Investimentos** (para coletar dados do WINJ26)
  - Terminal **ZeroMarkets** (para coletar dados do US500 e USDX)
- Os terminais devem estar **abertos e logados** antes de rodar o script
- Ambiente virtual Python (`venv`) ativado

---

## Instalação

1. **Clone ou acesse o projeto:**
   ```bash
   cd c:\Projetos\trading
   ```

2. **Crie o ambiente virtual (apenas na primeira vez):**
   ```bash
   python -m venv .venv
   ```

3. **Ative o ambiente virtual:**
   ```bash
   # Windows
   .venv\Scripts\activate
   ```

3. **Instale as dependências:**
   ```bash
   pip install -r requirements.txt
   ```

---

## Como executar

Com os dois terminais MT5 abertos e o ambiente virtual ativado, rode:

```bash
python leilao.py
```

O relatório aparece diretamente no terminal, com cores indicando o viés do mercado:
- 🟢 **Verde** → tendência de alta
- 🔴 **Vermelho** → tendência de baixa
- 🟡 **Amarelo** → cenário indefinido/neutro

---

## Ativos analisados

| Ativo    | Descrição                  | Fonte (Terminal) |
|----------|----------------------------|------------------|
| WINJ26   | Minicontrato de Índice     | Genial           |
| US500    | S&P 500 Futuro             | ZeroMarkets      |
| USDX     | Índice do Dólar (DXY)      | ZeroMarkets      |

> **Nota:** O ticker do WIN (ex: `WINJ26`) muda a cada vencimento. Atualize a variável `TICKER_WIN` no início do arquivo `leilao.py` conforme o contrato vigente.

---

## Estrutura relevante

```
trading/
├── leilao.py                      # Script principal
├── core/
│   ├── mt5_feed.py                # Conexão e coleta de dados do MT5
│   └── math_engine.py             # Cálculos de D-1 e variação overnight
└── strategies/
    └── analise_leilao.py          # Regras de negócio e geração do relatório
```
