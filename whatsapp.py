import os
import sys
import time
import pyperclip
import random
import psutil
import signal
import pyautogui

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
INTERVALO_SEGUNDOS = 230
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

def enviar_anuncio_com_imagem_e_texto(driver, caminho_imagem, texto_anuncio):
    try:
        # ---- ETAPA 1: CLICAR NO CLIPE DE PAPEL (BOTÃO DE ANEXO) ----
        print("-> Tentando clicar no botão de anexo (clipe de papel)...")
        anexar_btn = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//span[@data-icon='plus-rounded']"))
        )
        anexar_btn.click()
        time.sleep(2)

        # ---- ETAPA 2: CLICAR NO BOTÃO "FOTOS E VÍDEOS" ----
        print("-> Botão de anexo clicado. Tentando clicar em 'Fotos e vídeos'...")
        fotos_videos_btn = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="app"]/div/span[6]/div/ul/div/div/div[2]/li/div/div'))
        )
        fotos_videos_btn.click()
        time.sleep(3)
        
        # ---- ETAPA 3: ENVIAR O CAMINHO DO ARQUIVO (MÉTODO COM PYAUTOGUI) ----
        caminho_absoluto = os.path.abspath(caminho_imagem)
        if not os.path.exists(caminho_absoluto):
            print(f"❌ Erro: O arquivo de imagem não existe no caminho: {caminho_absoluto}")
            return False

        print(f"-> A janela do explorador de arquivos foi aberta. Usando pyautogui para digitar o caminho.")
        time.sleep(2)
        pyautogui.write(caminho_absoluto)
        time.sleep(1)
        pyautogui.press('enter')
        
        print("✅ Imagem carregada no campo de upload.")
        
        # ---- ETAPA 4: ENCONTRAR O CAMPO DE LEGENDA ----
        print("-> Aguardando a tela de pré-visualização da imagem...")
        
        print("-> Tentando encontrar o campo de legenda...")
        caixa_legenda = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//div[@aria-label='Adicione uma legenda']"))
        )
        
        pyperclip.copy(texto_anuncio)
        caixa_legenda.click()
        caixa_legenda.send_keys(Keys.CONTROL, 'v')
        print("✅ Texto da legenda colado.")

        # ---- ETAPA 5: CLICAR NO BOTÃO DE ENVIAR ----
        print("-> Tentando encontrar e clicar no botão de enviar...")
        enviar_btn = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//span[@data-icon='wds-ic-send-filled']"))
        )
        enviar_btn.click()
        print("✅ Anúncio enviado com sucesso.")
        time.sleep(2)
        return True

    except Exception as e:
        print(f"❌ Erro ao enviar o anúncio: {e}")
        try:
            cancelar_btn = driver.find_element(By.XPATH, "//span[@data-icon='x-alt']")
            cancelar_btn.click()
            time.sleep(1)
        except:
            pass
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

    pasta_anuncios = os.path.join(diretorio_saida, "dados/anuncios")
    pasta_enviados = os.path.join(diretorio_saida, "dados/enviados")
    os.makedirs(pasta_enviados, exist_ok=True)

    if not os.path.exists(pasta_anuncios):
        print(f"❌ Pasta '{pasta_anuncios}' não encontrada. Crie essa pasta e coloque os arquivos .txt e .jpg nela.")
        return

    arquivos_txt = [f for f in os.listdir(pasta_anuncios) if f.endswith(".txt")]
    if not arquivos_txt:
        print(f"❌ Nenhum anúncio (arquivo .txt) encontrado na pasta '{pasta_anuncios}'.")
        return

    random.shuffle(arquivos_txt)

    driver = iniciar_whatsapp()
    if not driver:
        return

    sucessos = 0
    tentativas = 0
    MAX_TENTATIVAS = len(arquivos_txt) * 2

    while sucessos < quantidade and tentativas < MAX_TENTATIVAS and arquivos_txt:
        arquivo_txt = arquivos_txt.pop(0)
        base_nome, _ = os.path.splitext(arquivo_txt)
        
        caminho_imagem = os.path.join(pasta_anuncios, f"{base_nome}.jpg")
        caminho_txt = os.path.join(pasta_anuncios, arquivo_txt)
        
        if not os.path.exists(caminho_imagem):
            print(f"❌ Imagem correspondente '{base_nome}.jpg' não encontrada. Pulando para o próximo anúncio.")
            tentativas += 1
            continue

        with open(caminho_txt, "r", encoding="utf-8") as f:
            texto_anuncio = f.read()

        print(f"\n📤 Tentando enviar anúncio ({sucessos+1}/{quantidade}): {base_nome}")
        enviado = enviar_anuncio_com_imagem_e_texto(driver, caminho_imagem, texto_anuncio)

        if enviado:
            sucessos += 1
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            
            novo_nome_base = f"{base_nome}_{timestamp}"
            
            novo_caminho_txt = os.path.join(pasta_enviados, f"{novo_nome_base}.txt")
            os.rename(caminho_txt, novo_caminho_txt)
            
            novo_caminho_imagem = os.path.join(pasta_enviados, f"{novo_nome_base}.jpg")
            os.rename(caminho_imagem, novo_caminho_imagem)
            
            print(f"✅ Anúncio (imagem e texto) movido para '{pasta_enviados}' com timestamp.")
        else:
            print("❌ Falha ao enviar. Pulando para o próximo arquivo.")

        tentativas += 1
        if sucessos < quantidade:
            print(f"⏳ Aguardando {INTERVALO_SEGUNDOS} segundos antes do próximo envio...")
            time.sleep(INTERVALO_SEGUNDOS)

    print(f"\n✅ Finalizado: {sucessos} anúncios enviados com sucesso.")
    
    print("⏳ Aguardando 5 segundos para o último envio ser processado...")
    time.sleep(5)
    
    driver.quit()
    sys.exit(0)

if __name__ == "__main__":
    main()