import os
import subprocess
import platform
import sys

VENV_NAME = "venv_bot"  # Nome do ambiente virtual
REQUIREMENTS_FILE = "requirements.txt"  # Arquivo de dependências

def verificar_python():
    """Verifica se o Python está instalado e qual comando usar"""
    try:
        # Tenta python3 primeiro
        subprocess.run(["python3", "--version"], check=True, capture_output=True)
        return "python3"
    except:
        try:
            # Fallback para python
            subprocess.run(["python", "--version"], check=True, capture_output=True)
            return "python"
        except:
            print("❌ Python não encontrado. Por favor, instale Python primeiro.")
            sys.exit(1)

def criar_venv(python_cmd):
    """Cria o ambiente virtual se não existir"""
    if not os.path.exists(VENV_NAME):
        print(f"🛠️ Criando ambiente virtual '{VENV_NAME}'...")
        subprocess.run([python_cmd, "-m", "venv", VENV_NAME], check=True)
    else:
        print(f"✅ Ambiente virtual '{VENV_NAME}' já existe.")

def instalar_dependencias():
    """Instala as dependências do requirements.txt"""
    if os.path.exists(REQUIREMENTS_FILE):
        print(f"📦 Instalando dependências de {REQUIREMENTS_FILE}...")
        
        # Comando de instalação multiplataforma
        if platform.system() == 'Windows':
            pip_cmd = os.path.join(VENV_NAME, "Scripts", "pip")
        else:
            pip_cmd = os.path.join(VENV_NAME, "bin", "pip")
        
        subprocess.run([pip_cmd, "install", "-r", REQUIREMENTS_FILE], check=True)
    else:
        print(f"⚠️ Arquivo {REQUIREMENTS_FILE} não encontrado. Continuando sem instalar dependências.")

def main():
    try:
        print("--- Iniciando Configuração do Ambiente ---")
        python_cmd = verificar_python()
        criar_venv(python_cmd)
        instalar_dependencias()
        print("\n✅ Ambiente configurado com sucesso!")
        print(f"Para ativar, use o comando apropriado para seu sistema:")
        if platform.system() == 'Windows':
            print(f"-> .\\{VENV_NAME}\\Scripts\\activate")
        else:
            print(f"-> source {VENV_NAME}/bin/activate")
    except Exception as e:
        print(f"❌ Erro durante a configuração: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()