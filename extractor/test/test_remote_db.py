# test_remote_db.py
import os
from sqlalchemy import create_engine, text
from sshtunnel import SSHTunnelForwarder
from urllib.parse import quote_plus
from dotenv import load_dotenv

load_dotenv()

# Carrega variáveis de ambiente
SSH_HOST = os.getenv("SSH_HOST")
SSH_PORT = int(os.getenv("SSH_PORT", 22))
SSH_USER = os.getenv("SSH_USER")
SSH_PASS = os.getenv("SSH_PASS")

REMOTE_USER = os.getenv("REMOTE_DB_USER")
REMOTE_PASS = quote_plus(os.getenv("REMOTE_DB_PASS"))
REMOTE_DB   = os.getenv("REMOTE_DB_NAME")
REMOTE_PORT = int(os.getenv("REMOTE_DB_PORT", 3306))

with SSHTunnelForwarder(
    (SSH_HOST, SSH_PORT),
    ssh_username=SSH_USER,
    ssh_password=SSH_PASS,
    remote_bind_address=("127.0.0.1", REMOTE_PORT)
) as tunnel:
    local_port = tunnel.local_bind_port
    url = f"mysql+pymysql://{REMOTE_USER}:{REMOTE_PASS}@127.0.0.1:{local_port}/{REMOTE_DB}"
    print("Tentando conectar em:", url)
    engine = create_engine(url)
    with engine.connect() as conn:
        result = conn.execute(text("SHOW TABLES"))
        tables = [row[0] for row in result]
        print("Tabelas remotas encontradas:", tables)
