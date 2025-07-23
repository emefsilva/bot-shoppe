import subprocess
import sys
from pathlib import Path

def instalar_dependencias():
    requirements_path = Path(__file__).parent / "requirements.txt"
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(requirements_path)], check=True)
        print("✅ Dependências instaladas com sucesso.")
    except subprocess.CalledProcessError:
        print("❌ Erro ao instalar as dependências.")
        sys.exit(1)

def rodar_script(nome_script, args=None, timeout=300):
    script_path = Path(__file__).parent / nome_script
    cmd = [sys.executable, str(script_path)]
    if args:
        cmd += args
    try:
        subprocess.run(cmd, check=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        print(f"⏰ Tempo limite excedido ao executar {nome_script}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro na execução de {nome_script}: {e}")

if __name__ == "__main__":
    instalar_dependencias()

    # Executa coletar_ofertas.py no modo automático, pedindo 100 produtos
    rodar_script("coletar_ofertas.py", args=["--auto", "100"], timeout=300)

    # Depois executa os outros scripts, também sem interação
    rodar_script("gerar_imagem.py", timeout=180)
    rodar_script("whatsapp.py", timeout=600)
