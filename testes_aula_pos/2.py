"""Exemplo de importação de função de outro módulo."""

# Como o arquivo se chama '1.py' (nome de arquivo inválido como módulo), usamos importlib.machinery
import os
from importlib.machinery import SourceFileLoader
from pathlib import Path

caminho_1 = Path(__file__).parent / "1.py"
if not caminho_1.exists():
    raise FileNotFoundError(f"Não foi possível encontrar {caminho_1}")

loader = SourceFileLoader("modulo1", str(caminho_1))
modulo1 = loader.load_module()

# usa a função saudacao do arquivo 1.py
saudacao = modulo1.saudacao


if __name__ == "__main__":
    saudacao("Thiago")
