# test_pymysql.py
import os
import pymysql
from sshtunnel import SSHTunnelForwarder
from dotenv import load_dotenv

load_dotenv()

SSH_HOST     = os.getenv("SSH_HOST")
SSH_PORT     = int(os.getenv("SSH_PORT", 22))
SSH_USER     = os.getenv("SSH_USER")
SSH_PASS     = os.getenv("SSH_PASS")

REMOTE_PORT  = int(os.getenv("REMOTE_DB_PORT", 3306))
DB_USER      = os.getenv("REMOTE_DB_USER")
DB_PASS      = os.getenv("REMOTE_DB_PASS")
DB_NAME      = os.getenv("REMOTE_DB_NAME")

with SSHTunnelForwarder(
    (SSH_HOST, SSH_PORT),
    ssh_username=SSH_USER,
    ssh_password=SSH_PASS,
    remote_bind_address=("127.0.0.1", REMOTE_PORT)
) as tunnel:
    local_port = tunnel.local_bind_port
    print("Túnel OK -> porta local:", local_port)
    conn = pymysql.connect(
        host="127.0.0.1",
        port=local_port,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        connect_timeout=10
    )
    with conn.cursor() as cur:
        cur.execute("SELECT 1;")
        print("SELECT 1 retornou:", cur.fetchone())
    conn.close()
