import os
from sqlalchemy import create_engine, inspect
from dotenv import load_dotenv

load_dotenv("../../.env")  # ajuste o caminho se necessário

LOCAL_DB_URL = os.getenv("LOCAL_DB_URL")
print("Tentando conectar em:", LOCAL_DB_URL)

engine = create_engine(LOCAL_DB_URL)
inspector = inspect(engine)

tables = inspector.get_table_names()
print("Tabelas locais encontradas:", tables)
