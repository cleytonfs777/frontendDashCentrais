from sshtunnel import SSHTunnelForwarder
import os
from dotenv import load_dotenv

load_dotenv()

SSH_HOST = os.getenv("SSH_HOST")
SSH_PORT = int(os.getenv("SSH_PORT", 22))
SSH_USER = os.getenv("SSH_USER")
SSH_PASS = os.getenv("SSH_PASS")

print(f"SSH_HOST: {SSH_HOST}")
print(f"SSH_PORT: {SSH_PORT}")
print(f"SSH_USER: {SSH_USER}")
print(f"SSH_PASS: {SSH_PASS}")

with SSHTunnelForwarder(
    (SSH_HOST, SSH_PORT),
    ssh_username=SSH_USER,
    ssh_password=SSH_PASS,
    remote_bind_address=("127.0.0.1", 3306)  # porta do MariaDB remoto
) as tunnel:
    print("SSH tunnel open:")
    print("  local bind port =", tunnel.local_bind_port)
    # mantém aberto por alguns segundos
    import time; time.sleep(5)


(venv) ad1429240@api-siad:~/centrais_telefonicas_api_v1/extractor/test$ python test_ssh.py

SSH tunnel open:
  local bind port = 39393
