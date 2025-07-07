import os
import pandas as pd
import paramiko
from sshtunnel import SSHTunnelForwarder
from sqlalchemy import create_engine, text
import pymysql
from dotenv import load_dotenv
load_dotenv(dotenv_path="../.env")  # se estiver na raiz do projeto

# Carrega variáveis do ambiente
SSH_HOST = os.getenv("SSH_HOST")
SSH_PORT = int(os.getenv("SSH_PORT", 22))
SSH_USER = os.getenv("SSH_USER")
SSH_PASS = os.getenv("SSH_PASS")

REMOTE_DB_HOST = os.getenv("REMOTE_DB_HOST", "127.0.0.1")
REMOTE_DB_PORT = int(os.getenv("REMOTE_DB_PORT", 3306))
REMOTE_DB_USER = os.getenv("REMOTE_DB_USER")
REMOTE_DB_PASS = os.getenv("REMOTE_DB_PASS")
REMOTE_DB_NAME = os.getenv("REMOTE_DB_NAME")

LOCAL_DB_URL = os.getenv("LOCAL_DB_URL")
# LOCAL_DB_URL = os.getenv("HOST_DB_URL")
COB_ID = 2  # fixo por enquanto

QUERY = """
    SELECT datahora, duracao, fila, holdtime, teleatendente, estado
    FROM meso_detalhe
"""

ESTADO_MAP = {"atendida": 1, "abandonado": 0}

def extract_and_load():
    with SSHTunnelForwarder(
        (SSH_HOST, SSH_PORT),
        ssh_username=SSH_USER,
        ssh_password=SSH_PASS,
        remote_bind_address=(REMOTE_DB_HOST, REMOTE_DB_PORT)
    ) as tunnel:
        print("Túnel SSH aberto. Extraindo dados...")

        conn_str = f"mysql+pymysql://{REMOTE_DB_USER}:{REMOTE_DB_PASS}@127.0.0.1:{tunnel.local_bind_port}/{REMOTE_DB_NAME}"
        remote_engine = create_engine(conn_str)

        with remote_engine.connect() as conn:
            df = pd.read_sql(QUERY, conn)

        # Divide datahora em data e hora
        df["data"] = pd.to_datetime(df["datahora"]).dt.date
        df["hora"] = pd.to_datetime(df["datahora"]).dt.time
        df.drop(columns=["datahora"], inplace=True)

        # Substitui NULL por 0 em duracao e holdtime
        df["duracao"] = df["duracao"].fillna(0).astype(int)
        df["holdtime"] = df["holdtime"].fillna(0).astype(int)

        # Mapeia estado para número
        df["estado"] = df["estado"].map(ESTADO_MAP).fillna(-1).astype(int)

        print(f"Dados extraídos: {len(df)} registros.")

        # Conecta ao banco local (PostgreSQL)
        local_engine = create_engine(LOCAL_DB_URL)

        # Cria a tabela com tipos corretos antes de inserir
        create_table_sql = '''
        CREATE TABLE IF NOT EXISTS fato_chamadas (
            data DATE,
            hora TIME,
            duracao INTEGER,
            fila VARCHAR(10),
            holdtime INTEGER,
            teleatendente VARCHAR(100),
            estado INTEGER
        );
        '''
        with local_engine.begin() as conn:
            conn.execute(text("DROP TABLE IF EXISTS fato_chamadas"))
            conn.execute(text(create_table_sql))
            df.to_sql("fato_chamadas", conn, index=False, if_exists="append")
            print("✅ Dados carregados em fato_chamadas.")

if __name__ == "__main__":
    extract_and_load()
