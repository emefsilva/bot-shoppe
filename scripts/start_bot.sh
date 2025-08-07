#!/bin/bash
echo "==================================="
echo "  INICIANDO O BOT DE OFERTAS SHOPEE"
echo "==================================="

echo ""
echo "[1/2] Ativando o ambiente virtual..."
source venv_bot/bin/activate

echo ""
echo "[2/2] Iniciando os processos..."
echo "     -> Servidor da API (em segundo plano)"
uvicorn api:app --host 0.0.0.0 &

# Guarda o ID do processo da API para poder finalizá-lo depois, se necessário
API_PID=$!
echo "     -> API rodando com PID: $API_PID"

echo "     -> Gerenciador de Fluxo (em primeiro plano)"
python fluxo.py

# Se o fluxo.py for interrompido, finaliza a API também
kill $API_PID
echo "Bot finalizado."