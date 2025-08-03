import os
import sys
import time
import subprocess
import requests
from filelock import FileLock, Timeout

# === CONFIGURAÇÕES PRINCIPAIS ===
TOTAL_CICLOS = 8  
CICLO_COMPLETO = 3  
ANUNCIOS_POR_CICLO = 6  
INTERVALO_ENTRE_CICLOS = 3600

# === CONFIGURAÇÕES TÉCNICAS ===
TENTATIVAS_MAXIMAS = 5  
TEMPO_ESPERA_FALHA = 60  
LOCK_FILE = "/tmp/fluxo_bot.lock"

def verificar_conexao():
    try:
        requests.get("https://www.google.com", timeout=10)
        return True
    except requests.ConnectionError:
        return False

def rodar_script(script, args=None):
    comando = ["python3", script]
    if args:
        comando += args
    
    for tentativa in range(TENTATIVAS_MAXIMAS):
        try:
            print(f"▶️ Tentativa {tentativa + 1} de {TENTATIVAS_MAXIMAS}: Executando {' '.join(comando)}")
            subprocess.run(comando, check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Falha na execução: {e}")
            if tentativa < TENTATIVAS_MAXIMAS - 1:
                print(f"🕒 Aguardando {TEMPO_ESPERA_FALHA} segundos antes de tentar novamente...")
                time.sleep(TEMPO_ESPERA_FALHA)
            else:
                print("⚠️ Número máximo de tentativas alcançado. Continuando...")
                return False
    return True

def instalar_requisitos():
    arquivos = ["coletar_ofertas.py", "gerar_imagem.py", "whatsapp.py"]
    for arquivo in arquivos:
        if not os.path.exists(arquivo):
            raise FileNotFoundError(f"Script não encontrado: {arquivo}")

def esperar_conexao():
    while not verificar_conexao():
        print("🌐 Sem conexão com a internet. Aguardando...")
        time.sleep(TEMPO_ESPERA_FALHA * 2)

def main():
    lock = FileLock(LOCK_FILE)
    try:
        lock.acquire(timeout=1)
    except Timeout:
        print("❌ O script já está rodando. Abortando.")
        return

    try:
        instalar_requisitos()
        
        for ciclo in range(1, TOTAL_CICLOS + 1):
            hora_atual = time.strftime("%H:%M")
            print(f"\n=== Ciclo {ciclo}/{TOTAL_CICLOS} | Hora {hora_atual} ===")
            
            esperar_conexao()

            if ciclo == 1 or ciclo % CICLO_COMPLETO == 0:
                print("→ Coletando e gerando novas ofertas...")
                qtd_anuncios_coleta = ANUNCIOS_POR_CICLO * CICLO_COMPLETO
                
                # Chamada do coletar_ofertas.py agora é simples e funcional
                if not rodar_script("coletar_ofertas.py", [str(qtd_anuncios_coleta)]):
                    print("⚠️ Falha na coleta de ofertas. Pulando para o próximo ciclo...")
                    continue

                if not rodar_script("gerar_imagem.py"):
                    print("⚠️ Falha na geração de imagens. Pulando para o próximo ciclo...")
                    continue

            print("→ Enviando via WhatsApp...")
            if not rodar_script("whatsapp.py", [str(ANUNCIOS_POR_CICLO)]):
                print("⚠️ Falha no envio via WhatsApp. Continuando para o próximo ciclo...")

            if ciclo < TOTAL_CICLOS:
                print(f"🕒 Aguardando {INTERVALO_ENTRE_CICLOS // 60} minutos para o próximo ciclo...")
                time.sleep(INTERVALO_ENTRE_CICLOS)

        print("✅ Todos os ciclos concluídos.")

    except Exception as e:
        print(f"❌ Erro crítico: {str(e)}")
    finally:
        lock.release()
        print("🔒 Lock liberado.")

if __name__ == "__main__":
    main()