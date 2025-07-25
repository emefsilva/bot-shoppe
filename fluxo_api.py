import requests
import time
import subprocess
import signal
import os
import psutil

URL_BASE = "http://localhost:8000"
TOTAL_CICLOS = 4
ANUNCIOS_POR_CICLO = 1
TEMPO_ENTRE_CICLOS = 30  # 1 hora

def aguardar_com_contador(segundos_total, passo=60):
    for restante in range(segundos_total, 0, -passo):
        minutos = restante // 60
        segundos = restante % 60
        print(f"⏳ Aguardando {minutos}m {segundos:02d}s...", end="\r")
        time.sleep(passo)
    print("\n⏱️ Próximo ciclo iniciado.\n")

def finalizar_whatsapp():
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmd = proc.info['cmdline']
            if cmd and 'whatsapp.py' in " ".join(cmd):
                print(f"🛑 Encerrando whatsapp.py (PID {proc.pid})")
                os.kill(proc.pid, signal.SIGTERM)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    # Encerra o Chrome com o perfil correto
    os.system("pkill -f 'chrome.*user-data-dir=/home/linuxlite/.config/google-chrome'")

for i in range(TOTAL_CICLOS):
    print(f"\n=== Ciclo {i+1}/{TOTAL_CICLOS} | Hora {8 + i}:00 ===")

    try:
        print("→ Coletando ofertas...")
        requests.post(f"{URL_BASE}/coletar-ofertas?qtd=20")

        print("→ Gerando imagens...")
        requests.post(f"{URL_BASE}/gerar-imagem")

        print("→ Enviando via WhatsApp...")
        response = requests.post(f"{URL_BASE}/enviar-whatsapp?quantidade={ANUNCIOS_POR_CICLO}")
        print("🟢 Envio concluído. Log:\n", response.json())

    except Exception as e:
        print(f"❌ Erro durante ciclo {i+1}: {e}")

    # Encerra processos antes de novo ciclo
    finalizar_whatsapp()

    if i < TOTAL_CICLOS - 1:
        print("🕒 Aguardando até o próximo envio...")
        aguardar_com_contador(TEMPO_ENTRE_CICLOS)
