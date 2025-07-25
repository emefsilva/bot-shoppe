#!/bin/bash

# Caminho base
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Ativar ambiente virtual se houver
if [ -f "$BASE_DIR/venv/bin/activate" ]; then
  source "$BASE_DIR/venv/bin/activate"
fi

# ✅ Garante que as dependências estão instaladas
echo "📦 Instalando dependências..."
pip install -r "$BASE_DIR/requirements.txt"

# Inicia a API FastAPI com uvicorn em segundo plano
echo "🚀 Iniciando FastAPI..."
nohup uvicorn api:app --host 127.0.0.1 --port 8000 > "$BASE_DIR/logs/api.log" 2>&1 &

# Espera alguns segundos para garantir que a API está de pé
sleep 5

# Inicia o fluxo contínuo
echo "🔁 Iniciando fluxo automático a cada 1 hora..."
nohup python3 "$BASE_DIR/fluxo_api.py" > "$BASE_DIR/logs/fluxo.log" 2>&1 &
