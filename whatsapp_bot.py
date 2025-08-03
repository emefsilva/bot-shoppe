import os
import sys
import time
import pyperclip
import requests
import json
import hashlib
import pyautogui
from pathlib import Path
from filelock import FileLock, Timeout
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image

# === CONFIGURAÇÕES GLOBAIS ===
APP_ID = "18341780685"
APP_SECRET = "FW3M3FW3EJDVSQBLQA7FVIHEBHDEYDES"
ENDPOINT = "https://open-api.affiliate.shopee.com.br/graphql"
PASTA_TEMP = Path("dados/temp")
PASTA_TEMP.mkdir(parents=True, exist_ok=True)
LOCK_FILE = "/tmp/whatsapp_bot.lock"

# === FUNÇÕES DE INTEGRAÇÃO COM A API SHOPEE ===
def gerar_signature(app_id, timestamp, payload, secret):
    texto = f"{app_id}{timestamp}{payload}{secret}"
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()

def buscar_produtos_shopee(termo_busca, limite=1):
    """Busca um único produto na API da Shopee com um termo de busca."""
    query = """
    query productSearch($keyword: String!, $limit: Int!) {
      productSearch(keyword: $keyword, limit: $limit, sortType: 4) {
        nodes {
          productName
          offerLink
          imageUrl
          priceMin
          priceDiscountRate
        }
      }
    }
    """

    variables = {"keyword": termo_busca, "limit": limite}
    payload = {"query": query, "variables": variables}
    payload_json = json.dumps(payload, separators=(',', ':'))
    timestamp = int(time.time())
    signature = gerar_signature(APP_ID, timestamp, payload_json, APP_SECRET)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"SHA256 Credential={APP_ID}, Timestamp={timestamp}, Signature={signature}",
        "User-Agent": "Mozilla/5.0"
    }

    try:
        response = requests.post(ENDPOINT, headers=headers, data=payload_json, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        if "errors" in data:
            print(f"❌ Erro na API: {data['errors']}")
            return None

        produtos = data.get("data", {}).get("productSearch", {}).get("nodes", [])
        return produtos[0] if produtos else None
    except requests.exceptions.RequestException as req_error:
        print(f"❌ Erro na requisição da API: {req_error}")
        return None

def baixar_imagem(url_imagem, nome_arquivo):
    """Baixa e salva a imagem do produto em uma pasta temporária."""
    try:
        resposta = requests.get(url_imagem, stream=True, timeout=10)
        resposta.raise_for_status()
        
        caminho_imagem = PASTA_TEMP / f"{nome_arquivo}.jpg"
        with open(caminho_imagem, 'wb') as f:
            for chunk in resposta.iter_content(1024):
                f.write(chunk)
        
        return caminho_imagem
    except Exception as e:
        print(f"⚠️ Erro ao baixar imagem: {e}")
        return None

# === FUNÇÕES DE AUTOMAÇÃO COM WHATSAPP ===
def adquirir_lock():
    lock = FileLock(LOCK_FILE)
    try:
        lock.acquire(timeout=1)
        return lock
    except Timeout:
        print("❌ Outro processo já está rodando. Abortando.")
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
    print("🟡 Aguardando WhatsApp Web carregar e fazer login...")
    try:
        # ALTERADO: XPath para um seletor mais genérico
        # Agora ele espera pela lista de chats, que é um bom indicador de que a página carregou.
        WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.XPATH, "//div[@data-testid='chat-list']"))
        )
        print("✅ WhatsApp Web carregado com sucesso.")
    except Exception as e:
        print(f"❌ Não foi possível carregar o WhatsApp Web. Encerrando. Erro: {e}")
        driver.quit()
        return None

    return driver

def enviar_resposta(driver, produto):
    """Envia o produto como resposta no chat atual."""
    try:
        nome_arquivo = f"produto_{int(time.time())}"
        caminho_imagem = baixar_imagem(produto.get("imageUrl", ""), nome_arquivo)
        
        if not caminho_imagem:
            print("⚠️ Falha ao baixar a imagem. Enviando apenas o texto.")
            mensagem = (
                f"🛍️ {produto.get('productName', 'Produto sem nome')}\n\n"
                f"💸 Por: R${produto.get('priceMin', 0):.2f} 🔥\n"
                f"🏷️ Desconto: {produto.get('priceDiscountRate', 0)}%\n\n"
                f"🔗 Link para comprar: {produto.get('offerLink', '#')}"
            )
            pyperclip.copy(mensagem)
            caixa_texto = driver.find_element(By.XPATH, "//div[@title='Caixa de texto de mensagem']")
            caixa_texto.send_keys(Keys.CONTROL, 'v')
            caixa_texto.send_keys(Keys.ENTER)
            return True

        # ---- Lógica para enviar a imagem e o texto (adaptada do script anterior) ----
        print("-> Tentando clicar no botão de anexo...")
        anexar_btn = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//span[@data-icon='plus-rounded']"))
        )
        anexar_btn.click()
        time.sleep(2)

        print("-> Clicando em 'Fotos e vídeos'...")
        fotos_videos_btn = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="app"]/div/span[6]/div/ul/div/div/div[2]/li/div/div'))
        )
        fotos_videos_btn.click()
        time.sleep(3)
        
        caminho_absoluto = os.path.abspath(caminho_imagem)
        pyautogui.write(caminho_absoluto)
        time.sleep(1)
        pyautogui.press('enter')
        
        print("✅ Imagem carregada. Adicionando legenda...")
        
        caixa_legenda = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//div[@aria-label='Adicione uma legenda']"))
        )
        
        mensagem = (
            f"🛍️ {produto.get('productName', 'Produto sem nome')}\n\n"
            f"💸 Por: R${produto.get('priceMin', 0):.2f} 🔥\n"
            f"🏷️ Desconto: {produto.get('priceDiscountRate', 0)}%\n\n"
            f"🔗 Link para comprar: {produto.get('offerLink', '#')}"
        )
        pyperclip.copy(mensagem)
        caixa_legenda.click()
        caixa_legenda.send_keys(Keys.CONTROL, 'v')

        print("✅ Texto da legenda colado. Enviando...")
        enviar_btn = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//span[@data-icon='wds-ic-send-filled']"))
        )
        enviar_btn.click()
        print("✅ Resposta enviada com sucesso.")
        time.sleep(2)
        os.remove(caminho_imagem) # Limpa o arquivo temporário
        return True

    except Exception as e:
        print(f"❌ Erro ao enviar a resposta: {e}")
        return False

# === LOOP PRINCIPAL DO BOT ===
def main():
    lock = adquirir_lock()
    driver = iniciar_whatsapp()
    if not driver:
        return

    print("🤖 Bot iniciado. Aguardando mensagens...")
    while True:
        try:
            # Procura por chats com mensagens não lidas
            # O XPath abaixo busca pelo contador de mensagens não lidas
            chats_nao_lidos = driver.find_elements(By.XPATH, "//span[@data-testid='icon-unread-count']")
            
            if chats_nao_lidos:
                print(f"🔔 Encontrei {len(chats_nao_lidos)} chat(s) com mensagens não lidas!")
                
                for chat in chats_nao_lidos:
                    # Clica no chat para abri-lo
                    chat_pai = chat.find_element(By.XPATH, "./ancestor::div[@data-testid='chat-list-row']")
                    chat_pai.click()
                    time.sleep(2)
                    
                    # Lê a última mensagem do chat
                    mensagens = driver.find_elements(By.XPATH, "//div[contains(@class, 'message-out') or contains(@class, 'message-in')]")
                    ultima_mensagem = mensagens[-1].find_element(By.XPATH, ".//span[@dir='ltr']")
                    termo_busca = ultima_mensagem.text
                    print(f"Mensagem recebida: '{termo_busca}'")
                    
                    if termo_busca:
                        produto_encontrado = buscar_produtos_shopee(termo_busca)
                        if produto_encontrado:
                            enviar_resposta(driver, produto_encontrado)
                        else:
                            mensagem_sem_produto = "❌ Não encontrei nenhum produto com este termo."
                            pyperclip.copy(mensagem_sem_produto)
                            caixa_texto = driver.find_element(By.XPATH, "//div[@title='Caixa de texto de mensagem']")
                            caixa_texto.send_keys(Keys.CONTROL, 'v')
                            caixa_texto.send_keys(Keys.ENTER)
                    
                    time.sleep(5)
            
        except Exception as e:
            print(f"❌ Erro no loop principal: {e}")
            # Em caso de erro, tenta continuar ou reinicia
            time.sleep(10)
            
        print("💤 Aguardando por 30 segundos antes de checar novamente...")
        time.sleep(30)

if __name__ == "__main__":
    main()