# Base com Python
FROM python:3.10-slim

# Define variáveis de proxy (caso sejam passadas via build args)
ARG HTTP_PROXY
ARG HTTPS_PROXY
ENV http_proxy=$HTTP_PROXY
ENV https_proxy=$HTTPS_PROXY

# Diretório de trabalho
WORKDIR /app

# Copia arquivos da API
COPY . .

# Instala dependências
RUN pip install --upgrade pip && pip install -r requirements.txt

# Expõe a porta do FastAPI (por padrão 8000)
EXPOSE 8000

# Comando padrão
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
