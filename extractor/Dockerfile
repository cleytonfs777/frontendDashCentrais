# Base com suporte a Python e pip
FROM python:3.10-slim

# Define variáveis de proxy (caso sejam passadas via build args)
ARG HTTP_PROXY
ARG HTTPS_PROXY
ENV http_proxy=$HTTP_PROXY
ENV https_proxy=$HTTPS_PROXY

# Instala netcat para o script wait-for-db.sh
RUN apt-get update && apt-get install -y netcat-openbsd

# Diretório de trabalho no container
WORKDIR /app

# Copia arquivos do extractor para dentro do container
COPY . .

# Instala dependências
RUN pip install --upgrade pip && pip install -r requirements.txt

# Comando padrão (também pode ser definido no docker-compose)
COPY wait-for-db.sh /app/wait-for-db.sh
RUN chmod +x /app/wait-for-db.sh

CMD ["/app/wait-for-db.sh"]

