import subprocess

def rodar_script(nome, args=None, timeout=300):
    cmd = ["python", nome]
    if args:
        cmd += args
    try:
        subprocess.run(cmd, check=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        print(f"⏰ Tempo limite excedido ao executar {nome}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro na execução de {nome}: {e}")

if __name__ == "__main__":
    # Executa coletar_ofertas.py no modo automático, pedindo 100 produtos
    rodar_script("coletar_ofertas.py", args=["--auto", "100"], timeout=300)

    # Depois executa os outros scripts, também sem interação
    rodar_script("gerar_imagem.py", timeout=180)
    rodar_script("whatsapp.py", timeout=600)
