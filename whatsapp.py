# whatsapp.py

import os
import sys
import time
import random
import requests
from datetime import datetime
from pathlib import Path

# Dependências de automação
from filelock import FileLock, Timeout
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import pyperclip
import pyautogui

# === CONFIGURAÇÕES ===
API_URL = "http://localhost:8000"
NOME_GRUPO = "LoJai - Promoções do dia"
#NOME_GRUPO = "Teste shoppe"
INTERVALO_SEGUNDOS = 30
PASTA_ANUNCIOS = Path("dados/anuncios")
PASTA_ENVIADOS = Path("dados/enviados")
# Configuração de lock multiplataforma
if sys.platform == 'win32':
    LOCK_FILE = os.path.join(os.environ.get('TEMP', 'C:/Temp'), 'whatsapp_chrome.lock')
else:
    LOCK_FILE = "/tmp/whatsapp_chrome.lock"

# === FUNÇÕES DE APOIO E SELENIUM ===
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

def enviar_anuncio_com_imagem_e_texto(driver, caminho_imagem, texto_anuncio):
    try:
        # ETAPA 1: CLICAR NO BOTÃO DE ANEXO
        anexar_btn = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//span[@data-icon='plus-rounded']"))
        )
        anexar_btn.click()
        time.sleep(2)

        # ETAPA 2: CLICAR NO BOTÃO "FOTOS E VÍDEOS"
        fotos_videos_btn = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="app"]/div/span[6]/div/ul/div/div/div[2]/li/div/div'))
        )
        fotos_videos_btn.click()
        time.sleep(3)
        
        # ETAPA 3: ENVIAR O CAMINHO DO ARQUIVO COM PYAUTOGUI
        caminho_absoluto = os.path.abspath(caminho_imagem)
        if not os.path.exists(caminho_absoluto):
            print(f"❌ Erro: O arquivo de imagem não existe: {caminho_absoluto}")
            return False

        time.sleep(2)
        pyautogui.write(caminho_absoluto)
        time.sleep(1)
        pyautogui.press('enter')
        
        # ETAPA 4: COLAR A LEGENDA
        caixa_legenda = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//div[@aria-label='Adicione uma legenda']"))
        )
        pyperclip.copy(texto_anuncio)
        caixa_legenda.click()
        caixa_legenda.send_keys(Keys.CONTROL, 'v')

        # ETAPA 5: ENVIAR
        enviar_btn = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//span[@data-icon='wds-ic-send-filled']"))
        )
        enviar_btn.click()
        print("✅ Anúncio enviado com sucesso via Selenium.")
        time.sleep(2)
        return True

    except Exception as e:
        print(f"❌ Erro durante a automação do envio: {e}")
        try:
            cancelar_btn = driver.find_element(By.XPATH, "//span[@data-icon='x-alt']")
            cancelar_btn.click()
        except:
            pass
        return False

def registrar_envio_na_api(item_id: str):
    """Chama a API para marcar um item como enviado no banco de dados."""
    try:
        endpoint = f"{API_URL}/api/registrar-envios"
        payload = [{"itemId": item_id, "sent_at": datetime.now().isoformat()}]
        response = requests.post(endpoint, json=payload, timeout=10)
        response.raise_for_status()
        print(f"  ✅ API notificada. Item {item_id} marcado como enviado.")
        return True
    except requests.RequestException as e:
        print(f"  ❌ Erro ao notificar API para o item {item_id}: {e}")
        return False

# === FUNÇÃO PRINCIPAL ===
def main():
    lock = adquirir_lock()
    PASTA_ENVIADOS.mkdir(parents=True, exist_ok=True)
    
    limite_envios = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else float('inf')

    arquivos_txt = sorted([f for f in os.listdir(PASTA_ANUNCIOS) if f.endswith(".txt")])
    if not arquivos_txt:
        print("✅ Nenhum anúncio para enviar."); lock.release(); return

    driver = iniciar_whatsapp()
    if not driver:
        lock.release(); return

    print(f"🚀 Iniciando envio de até {limite_envios if limite_envios != float('inf') else len(arquivos_txt)} anúncios...")
    enviados_nesta_sessao = 0
    for arquivo_txt in arquivos_txt:
        if enviados_nesta_sessao >= limite_envios:
            print("✋ Limite de envios para esta sessão atingido.")
            break
            
        base_nome, _ = os.path.splitext(arquivo_txt)
        
        try:
            item_id = base_nome.split('_')[-1]
            if not item_id.isdigit(): continue
        except IndexError: continue

        caminho_imagem = PASTA_ANUNCIOS / f"{base_nome}.jpg"
        caminho_txt = PASTA_ANUNCIOS / arquivo_txt
        
        if not caminho_imagem.exists(): continue

        with open(caminho_txt, "r", encoding="utf-8") as f:
            texto_anuncio = f.read()

        print(f"\n📤 Enviando anúncio do item ID: {item_id}")
        enviado_com_sucesso = enviar_anuncio_com_imagem_e_texto(driver, caminho_imagem, texto_anuncio)

        if enviado_com_sucesso:
            enviados_nesta_sessao += 1
            registrar_envio_na_api(item_id)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            os.rename(caminho_txt, PASTA_ENVIADOS / f"{base_nome}_{timestamp}.txt")
            os.rename(caminho_imagem, PASTA_ENVIADOS / f"{base_nome}_{timestamp}.jpg")
        else:
            print(f"❌ Falha no envio do item {item_id}.")

        time.sleep(INTERVALO_SEGUNDOS)

    print("\n✅ Fim do processo de envio.")
    driver.quit()
    lock.release()

if __name__ == "__main__":
    main()