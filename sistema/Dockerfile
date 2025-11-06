FROM python:3.11-slim

# Configurar o proxy para o build
ENV http_proxy=http://proxymg.prodemge.gov.br:8080
ENV https_proxy=http://proxymg.prodemge.gov.br:8080

WORKDIR /app

COPY requirements.txt .

# pip com proxy já ativado via ENV
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8050

ENV PYTHONUNBUFFERED=1

CMD ["python", "app.py"]