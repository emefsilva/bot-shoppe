import os
import sys
import time
import pyperclip
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

def iniciar_whatsapp():
    chrome_options = Options()
    user_data_dir = os.path.abspath("chrome_profile")
    chrome_options.add_argument(f"--user-data-dir={user_data_dir}")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.get("https://web.whatsapp.com")
    print("🟡 Aguardando WhatsApp Web carregar...")
    time.sleep(10)  # tempo inicial para carregar

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

def main():
    diretorio_saida = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    pasta_imagem = os.path.join(diretorio_saida, "dados/imagem")

    if not os.path.exists(pasta_imagem):
        print(f"❌ Pasta '{pasta_imagem}' não encontrada.")
        return

    arquivos = sorted([f for f in os.listdir(pasta_imagem) if f.startswith("anuncio_")])
    if not arquivos:
        print("❌ Nenhum anúncio encontrado.")
        return

    driver = iniciar_whatsapp()

    if not driver:
        return

    for i, arquivo in enumerate(arquivos, 1):
        caminho = os.path.join(pasta_imagem, arquivo)
        with open(caminho, "r", encoding="utf-8") as f:
            mensagem = f.read()

        print(f"\n📤 Enviando anúncio {i} de {len(arquivos)}...")
        print(mensagem)

        enviar_com_copiar_colar(driver, mensagem)

        if i < len(arquivos):
            print(f"⏳ Aguardando {INTERVALO_SEGUNDOS} segundos...")
            time.sleep(INTERVALO_SEGUNDOS)

    print("\n✅ Todos os anúncios foram enviados com sucesso!")
    driver.quit()

if __name__ == "__main__":
    main()
