from fastapi import FastAPI
from sqlalchemy import create_engine, text
import os

app = FastAPI(title="API Telefonia CBMMG")

DB_URL = os.getenv("LOCAL_DB_URL")
engine = create_engine(DB_URL)

@app.get("/")
def health_check():
    return {"status": "alive"}

@app.get("/api/fato_chamadas")
def get_fato_chamadas():
    query = text("""
        SELECT * FROM fato_chamadas 
        ORDER BY data DESC, hora DESC 
        LIMIT 1000
    """)
    with engine.connect() as conn:
        result = conn.execute(query).mappings().all()
        return result


# Você pode continuar adicionando os demais endpoints aqui

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
