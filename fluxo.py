import subprocess
import time
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
TOTAL_CICLOS = 4
INTERVALO_ENTRE_CICLOS = 30  # 1 hora
ANUNCIOS_POR_CICLO = 1

def rodar_script(nome, args=None):
    args = args or []
    caminho = BASE_DIR / nome
    print(f"▶️ Executando: {nome} {' '.join(args)}")
    
    result = subprocess.run(
        ["python3", str(caminho)] + args,
        env={**os.environ, "DISPLAY": ":0.0"},
    )

    print("🟢 Concluído.")
    return result.returncode

def main():
    for ciclo in range(1, TOTAL_CICLOS + 1):
        hora_atual = time.strftime("%H:%M")
        print(f"\n=== Ciclo {ciclo}/{TOTAL_CICLOS} | Hora {hora_atual} ===")

        print("→ Coletando ofertas...")
        rodar_script("coletar_ofertas.py", ["--auto", str(ANUNCIOS_POR_CICLO)])

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
