#!/bin/bash
set -e

DB_HOST=$(echo "$LOCAL_DB_URL" | sed -E 's|.*@([^:/]+):([0-9]+).*|\1|')
DB_PORT=$(echo "$LOCAL_DB_URL" | sed -E 's|.*@([^:/]+):([0-9]+).*|\2|')

echo "⏳ Aguardando banco de dados em $DB_HOST:$DB_PORT..."

until nc -z "$DB_HOST" "$DB_PORT"; do
  sleep 1
done

echo "✅ Banco de dados está pronto. Iniciando extractor.py..."
exec python extractor.py