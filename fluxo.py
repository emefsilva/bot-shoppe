import subprocess
import sys
import os
import time
from pathlib import Path
import time
import subprocess

TOTAL_CICLOS = 5
ANUNCIOS_POR_CICLO = 2
PAGINAS_ANUNCIOS = 5
INTERVALO_ENTRE_CICLOS = 3600  # 1 hora
CICLO_COMPLETO = 2  # a cada 3 ciclos, roda tudo

def instalar_requisitos():
    subprocess.run(["pip", "install", "-r", "requirements.txt"])

def rodar_script(script, args=[]):
    cmd = ["python", script] + args
    print(f"▶️ Executando: {' '.join(cmd)}")
    resultado = subprocess.run(cmd)
    return resultado.returncode

def main():
    instalar_requisitos()

    for ciclo in range(1, TOTAL_CICLOS + 1):
        hora_atual = time.strftime("%H:%M")
        print(f"\n=== Ciclo {ciclo}/{TOTAL_CICLOS} | Hora {hora_atual} ===")

        if ciclo == 1 or ciclo % CICLO_COMPLETO == 0:
            print("→ Coletando ofertas...")
            rodar_script("coletar_ofertas.py", ["--auto"])

            print("→ Gerando imagens...")
            rodar_script("gerar_imagem.py")

        print("→ Enviando via WhatsApp...")
        ret = rodar_script("whatsapp.py", [str(ANUNCIOS_POR_CICLO)])

        if ret != 0:
            print("❌ Erro no envio WhatsApp. Encerrando script.")
            break

        if ciclo < TOTAL_CICLOS:
            print(f"🕒 Aguardando {INTERVALO_ENTRE_CICLOS/60:.0f} minutos para o próximo ciclo...\n")
            time.sleep(INTERVALO_ENTRE_CICLOS)

    print("✅ Todos os ciclos concluídos.")

if __name__ == "__main__":
    main()
