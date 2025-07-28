import os
import sys
import time
import pyperclip
import random
import psutil
import signal

from filelock import FileLock, Timeout
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

NOME_GRUPO = "Teste shoppe"
INTERVALO_SEGUNDOS = 30
LOCK_FILE = "/tmp/whatsapp_chrome.lock"

# Função para aplicar o lock
def adquirir_lock():
    lock = FileLock(LOCK_FILE)
    try:
        lock.acquire(timeout=1)
        return lock
    except Timeout:
        print("❌ Outro processo já está usando o Chrome com esse perfil. Abortando.")
        sys.exit(1)

def iniciar_whatsapp():
    chrome_options = Options()
    user_data_dir = os.path.abspath("chrome_profile")
    chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    except Exception as e:
        print(f"❌ Erro ao iniciar Chrome: {e}")
        return None

    driver.get("https://web.whatsapp.com")
    print("🟡 Aguardando WhatsApp Web carregar...")
    time.sleep(10)

    try:
        grupo = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, f"//span[@title='{NOME_GRUPO}']"))
        )
        grupo.click()
        time.sleep(3)
        print("✅ Grupo encontrado rapidamente.")
    except:
        print("⚠️ Grupo não encontrado de imediato. Aguardando login/manual...")
        try:
            grupo = WebDriverWait(driver, 60).until(
                EC.presence_of_element_located((By.XPATH, f"//span[@title='{NOME_GRUPO}']"))
            )
            grupo.click()
            time.sleep(3)
            print("✅ Grupo encontrado após aguardar login.")
        except:
            print("❌ Grupo ainda não foi encontrado. Encerrando.")
            driver.quit()
            return None

    return driver

def aguardar_preview(driver, timeout=10):
    def condicao_preview(driver):
        try:
            elem = driver.find_element(By.CSS_SELECTOR, "div.x1c4vz4f.x2lah0s.xdl72j9.x14yy4lh")
            return elem.size['height'] >= 150
        except:
            return False
    try:
        WebDriverWait(driver, timeout).until(condicao_preview)
        return True
    except:
        return False

def enviar_com_copiar_colar(driver, mensagem):
    pyperclip.copy(mensagem)
    caixa = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true'][@data-tab='10']"))
    )
    caixa.click()
    time.sleep(1)
    caixa.send_keys(Keys.CONTROL, 'v')

    carregou = aguardar_preview(driver, timeout=10)

    if carregou:
        print("✅ Preview detectado, enviando mensagem...")
        caixa.send_keys(Keys.ENTER)
        time.sleep(2)
        return True
    else:
        print("⛔ Preview não carregado. Apagando e pulando...")
        caixa.send_keys(Keys.CONTROL, 'a')
        time.sleep(0.3)
        caixa.send_keys(Keys.BACKSPACE)
        time.sleep(1)
        return False

def finalizar_selenium_completamente():
    print("🛑 Encerrando processos do Selenium (chromedriver e chrome)...")
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmd = " ".join(proc.info['cmdline'])
            if "chrome" in cmd.lower() or "chromedriver" in cmd.lower():
                print(f"🔪 Matando processo: {cmd} (PID {proc.pid})")
                proc.send_signal(signal.SIGKILL)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    print("✅ Todos os processos do Selenium foram encerrados.")    

def main():
    lock = adquirir_lock()

    diretorio_saida = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].isdigit() else os.getcwd()
    quantidade = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 10

    pasta_imagem = os.path.join(diretorio_saida, "dados/imagem")
    pasta_imagem_enviadas = os.path.join(diretorio_saida, "dados/imagem_enviadas")
    os.makedirs(pasta_imagem_enviadas, exist_ok=True)

    if not os.path.exists(pasta_imagem):
        print(f"❌ Pasta '{pasta_imagem}' não encontrada.")
        return

    arquivos = [f for f in os.listdir(pasta_imagem) if f.startswith("anuncio_")]
    if not arquivos:
        print("❌ Nenhum anúncio encontrado.")
        return

    random.shuffle(arquivos)

    driver = iniciar_whatsapp()
    if not driver:
        return

    sucessos = 0
    tentativas = 0
    MAX_TENTATIVAS = len(arquivos) * 2

    while sucessos < quantidade and tentativas < MAX_TENTATIVAS and arquivos:
        arquivo = arquivos.pop(0)
        caminho = os.path.join(pasta_imagem, arquivo)

        with open(caminho, "r", encoding="utf-8") as f:
            mensagem = f.read()

        print(f"\n📤 Tentando enviar anúncio ({sucessos+1}/{quantidade}): {arquivo}")
        enviado = enviar_com_copiar_colar(driver, mensagem)

        if enviado:
            sucessos += 1
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            nome_novo_arquivo = arquivo.rsplit('.', 1)[0] + f"_{timestamp}.txt"
            novo_caminho = os.path.join(pasta_imagem_enviadas, nome_novo_arquivo)
            os.rename(caminho, novo_caminho)
            print(f"✅ Arquivo movido para '{pasta_imagem_enviadas}' com timestamp: {nome_novo_arquivo}")
        else:
            print("❌ Falha ao enviar. Pulando para o próximo arquivo.")

        tentativas += 1
        if sucessos < quantidade:
            print(f"⏳ Aguardando {INTERVALO_SEGUNDOS} segundos antes do próximo envio...")
            time.sleep(INTERVALO_SEGUNDOS)

    print(f"\n✅ Finalizado: {sucessos} anúncios enviados com sucesso.")
    driver.quit()
    # lock.release()  # Opcional: é liberado automaticamente ao sair
    sys.exit(0)

if __name__ == "__main__":
    main()
