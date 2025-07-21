import os
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

# CONFIGURAÇÕES
PASTA_ANUNCIOS = os.path.join(os.getcwd(), "imagem")
NOME_GRUPO = "Teste shoppe"
INTERVALO_SEGUNDOS = 30

def iniciar_whatsapp():
    chrome_options = Options()
    user_data_dir = os.path.abspath("chrome_profile")
    chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.get("https://web.whatsapp.com")
    print("🟡 Aguardando WhatsApp Web carregar...")
    time.sleep(10)

    try:
        grupo = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, f"//span[@title='{NOME_GRUPO}']"))
        )
        grupo.click()
        time.sleep(3)
    except:
        input("⚠️ Escaneie o QR code se necessário e pressione Enter...")
        grupo = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, f"//span[@title='{NOME_GRUPO}']"))
        )
        grupo.click()
        time.sleep(3)

    return driver

def aguardar_preview(driver, timeout=10):
    def condicao_preview(driver):
        try:
            elem = driver.find_element(By.CSS_SELECTOR, "div.x1c4vz4f.x2lah0s.xdl72j9.x14yy4lh")
            altura = elem.size['height']
            # Debug opcional: print(f"Altura do preview: {altura}px")
            return altura >= 150
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
    caixa.send_keys(Keys.CONTROL, 'v')  # Cola o texto

    # Espera alguns segundos para carregar o preview
    carregou = aguardar_preview(driver, timeout=10)

    if carregou:
        print("✅ Preview detectado (altura >= 150px), enviando mensagem...")
        caixa.send_keys(Keys.ENTER)
        time.sleep(2)
        return True
    else:
        print("⛔ Preview não carregado. Apagando e pulando...")
        # Limpa a caixa: CTRL+A + Backspace
        caixa.send_keys(Keys.CONTROL, 'a')
        time.sleep(0.3)
        caixa.send_keys(Keys.BACKSPACE)
        time.sleep(1)
        return False


def altura_preview_esperada(driver):
    # Espera até que a altura do elemento seja >= 150 (px)
    def condicao(driver):
        try:
            elem = driver.find_element(By.CSS_SELECTOR, "div.x1c4vz4f.x2lah0s.xdl72j9.x14yy4lh")
            altura = elem.size['height']
            return altura >= 150
        except:
            return False
    return WebDriverWait(driver, 10).until(condicao)    


def main():
    if not os.path.exists(PASTA_ANUNCIOS):
        print("❌ Pasta 'imagem' não encontrada.")
        return

    arquivos = sorted([f for f in os.listdir(PASTA_ANUNCIOS) if f.startswith("anuncio_")])
    if not arquivos:
        print("❌ Nenhum anúncio encontrado.")
        return

    driver = iniciar_whatsapp()

    for i, arquivo in enumerate(arquivos, 1):
        caminho = os.path.join(PASTA_ANUNCIOS, arquivo)
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
