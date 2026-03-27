# Log nos bastidores do nosso motor de trading. 
#
# Ele é responsável por registrar todas as ações, sinais e decisões tomadas pelo sistema, 
# permitindo que possamos analisar o desempenho e identificar pontos de melhoria. 
# O logger é configurado para criar um arquivo de log diário, 
# armazenando as informações de forma organizada e fácil de consultar.

import logging
import os
from datetime import datetime

def get_logger():
    # Cria a pasta 'logs' na raiz do projeto se ela não existir
    if not os.path.exists('logs'):
        os.makedirs('logs')
        
    # Cria um arquivo de log com a data de hoje
    hoje = datetime.now().strftime('%Y-%m-%d')
    arquivo_log = f"logs/quant_engine_{hoje}.log"
    
    # Configuração do Logger
    logger = logging.getLogger("QuantLogger")
    logger.setLevel(logging.INFO)
    
    # Garante que não vamos duplicar os logs se a função for chamada várias vezes
    if not logger.handlers:
        fh = logging.FileHandler(arquivo_log, encoding='utf-8')
        # Formato: [10:15:30] INFO - Sinal de COMPRA
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s - %(message)s', datefmt='%H:%M:%S')
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        
    return logger

# Instância global pronta para ser importada por qualquer outro arquivo
log = get_logger()