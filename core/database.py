# Tudo relacionado ao SQLite
# Aqui vive apenas o que toca no banco de dados. Se um dia migrarmos para o Postgres, só mexemos aqui.

import sqlite3

def inicializar_banco(nome_arquivo='dados_mercado.db'):
    conn = sqlite3.connect(nome_arquivo)
    cursor = conn.cursor()
    
    # Cria a tabela base
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historico_termometro (
            timestamp DATETIME PRIMARY KEY,
            win_close REAL,
            z_win REAL,
            z_sp500 REAL,
            z_dxy REAL,
            z_vix REAL,
            termometro_score REAL,
            sinal TEXT
        )
    ''')
    conn.commit()

    # Evolução do Banco (Adiciona colunas se não existirem)
    colunas_novas = ['vwap', 'dist_vwap_pts', 'vol_atual', 'vol_media']
    for col in colunas_novas:
        try:
            cursor.execute(f"ALTER TABLE historico_termometro ADD COLUMN {col} REAL")
            conn.commit()
        except sqlite3.OperationalError:
            pass # Coluna já existe

    return conn

def salvar_leitura(conn, dados):
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO historico_termometro 
            (timestamp, win_close, z_win, z_sp500, z_dxy, z_vix, 
             termometro_score, sinal, vwap, dist_vwap_pts, vol_atual, vol_media)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', dados)
        conn.commit()
    except Exception as e:
        print(f"Erro ao salvar no BD: {e}")