@echo off
echo ===================================
echo   INICIANDO O BOT DE OFERTAS SHOPEE
echo ===================================

echo.
echo [1/2] Ativando o ambiente virtual...
call .\venv_bot\Scripts\activate

echo.
echo [2/2] Iniciando os processos...
echo      -> Servidor da API (em uma nova janela)
start "API Server" uvicorn api:app --host 0.0.0.0

echo      -> Gerenciador de Fluxo (nesta janela)
python fluxo.py

pause