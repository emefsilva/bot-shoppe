import os
import sys
import time
import subprocess
from filelock import FileLock, Timeout

TOTAL_CICLOS = 6  # Quantidade total de ciclos por dia
CICLO_COMPLETO = 3  # A cada N ciclos, executa coleta e geração
ANUNCIOS_POR_CICLO = 10  # Quantos anúncios enviar por ciclo
INTERVALO_ENTRE_CICLOS = 3600  # 1 hora = 3600 segundos

LOCK_FILE = "/tmp/fluxo_bot.lock"

def rodar_script(script, args=None):
    comando = ["python3", script]
    if args:
        comando += args
    print(f"▶️ Executando: {' '.join(comando)}")
    resultado = subprocess.run(comando)
    return resultado.returncode

def instalar_requisitos():
    arquivos = ["coletar_ofertas.py", "gerar_imagem.py", "whatsapp.py"]
    for arquivo in arquivos:
        if not os.path.exists(arquivo):
            print(f"❌ Script não encontrado: {arquivo}")
            sys.exit(1)

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

            # Coleta e geração a cada CICLO_COMPLETO ciclos (inclusive o primeiro)
            if ciclo == 1 or ciclo % CICLO_COMPLETO == 0:
                print("→ Coletando ofertas...")
                rodar_script("coletar_ofertas.py", ["--auto"])

                print("→ Gerando imagens...")
                rodar_script("gerar_imagem.py")

            print("→ Enviando via WhatsApp...")
            ret = rodar_script("whatsapp.py", [str(ANUNCIOS_POR_CICLO)])

            if ret != 0:
                print("❌ Erro no envio via WhatsApp. Encerrando execução.")
                break

            if ciclo < TOTAL_CICLOS:
                print(f"🕒 Aguardando {INTERVALO_ENTRE_CICLOS // 60} minutos para o próximo ciclo...")
                time.sleep(INTERVALO_ENTRE_CICLOS)

        print("✅ Todos os ciclos concluídos.")

    finally:
        lock.release()

if __name__ == "__main__":
    main()
