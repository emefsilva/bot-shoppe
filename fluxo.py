# fluxo.py

import os
import sys
import time
import subprocess
import requests
from datetime import datetime

# === CONFIGURAÇÕES ===
API_URL = "http://localhost:8000"
INTERVALO_ENTRE_ENVIOS_MINUTOS = 15
ANUNCIOS_POR_LOTE_DE_ENVIO = 1
QUANTIDADE_GERACAO_PAGINA = 1
PORCENTAGEM_MINIMA_DESCONTO = 20

PASTA_DADOS = "dados"
FLAG_PREPARACAO_DIARIA = os.path.join(PASTA_DADOS, "preparacao_ok_{}.flag")

# === FUNÇÕES AUXILIARES ===
def verificar_api():
    print("🔍 Verificando status da API...")
    try:
        response = requests.get(f"{API_URL}/api/status/geral", timeout=5)
        response.raise_for_status()
        print("✅ API está online.")
        return True
    except requests.RequestException:
        print("❌ API offline. Inicie o servidor em outro terminal com: uvicorn api:app --reload")
        return False

def chamar_coleta_diaria():
    print("\n[PASSO 1 de 3] 📥 Acionando a coleta de produtos na API...")
    try:
        endpoint = f"{API_URL}/api/iniciar-coleta?ordenar_por=vendas"
        #endpoint = f"{API_URL}/api/iniciar-coleta?paginas={QUANTIDADE_GERACAO_PAGINA}&desconto_minimo={PORCENTAGEM_MINIMA_DESCONTO}"
        response = requests.post(endpoint, timeout=600)
        response.raise_for_status()
        print(f"✅ Coleta na API concluída: {response.json()}")
        return True
    except requests.RequestException as e:
        print(f"❌ Falha ao acionar a coleta na API: {e}")
        return False

def rodar_script_externo(script_nome: str, args: list = None):
    print(f"\n🚀 Executando '{script_nome}'...")
    try:
        comando = [sys.executable, script_nome]
        if args: comando.extend(args)
        subprocess.run(comando, check=True)
        print(f"✅ Script '{script_nome}' executado.")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"❌ Falha ao executar '{script_nome}': {e}")
        return False

# === FLUXO PRINCIPAL ===
def main():
    os.makedirs(PASTA_DADOS, exist_ok=True)
    if not verificar_api(): sys.exit(1)

    hoje = datetime.now().strftime("%Y-%m-%d")
    flag_arquivo_hoje = FLAG_PREPARACAO_DIARIA.format(hoje)

    if not os.path.exists(flag_arquivo_hoje):
        print(f"☀️ Bom dia! Iniciando a preparação para {hoje}.")
        if not chamar_coleta_diaria(): sys.exit(1)
        
        print("\n[PASSO 2 de 3] 🖼️  Gerando imagens e textos...")
        if not rodar_script_externo("gerar_imagem.py"): sys.exit(1)
        
        with open(flag_arquivo_hoje, 'w') as f: f.write("ok")
        print("\n✅ Preparação diária concluída.")
    else:
        print(f"👍 Preparação para {hoje} já foi feita. Indo para os envios.")

    print("\n[PASSO 3 de 3] 📲 Entrando no modo de envio contínuo...")
    while True:
        rodar_script_externo("whatsapp.py", [str(ANUNCIOS_POR_LOTE_DE_ENVIO)])
        print(f"😴 Próximo envio em {INTERVALO_ENTRE_ENVIOS_MINUTOS} minutos...")
        time.sleep(INTERVALO_ENTRE_ENVIOS_MINUTOS * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Fluxo interrompido pelo usuário. Até mais!")