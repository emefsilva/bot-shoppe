import json
from pathlib import Path
import threading
import sys
import time

# === Caminhos organizados ===
BASE_DIR = Path(__file__).parent
PASTA_DADOS = BASE_DIR / "dados"
ARQUIVO_JSON = PASTA_DADOS / "produtos_promocao.json"
PASTA_IMAGENS = PASTA_DADOS / "imagem"

# === Funções ===
def criar_pasta_imagens():
    """Cria a pasta 'dados/imagem' se não existir"""
    PASTA_IMAGENS.mkdir(parents=True, exist_ok=True)
    print("📂 Pasta 'dados/imagem' verificada/criada.")

def gerar_anuncio(produto):
    """Gera um anúncio com emojis e formatação melhorada"""
    preco_atual = produto['preco'].split(' ')[0]
    preco_original = produto['preco'].split('de ')[1].replace(')', '') if 'de' in produto['preco'] else ''
    
    anuncio = f"🛍️ {produto['nome']}\n\n"
    if preco_original:
        anuncio += f"de: ~{preco_original}~\n"
    anuncio += (
        f"💸 Por: {preco_atual} 🔥\n\n"
        f"👉 Link para comprar: {produto['link']}\n\n"
        f"_*Promoção sujeita a alteração a qualquer momento*_"
    )
    return anuncio

def salvar_anuncios(produtos):
    """Salva os anúncios em arquivos .txt na pasta dados/imagem"""
    criar_pasta_imagens()

    timestamp = time.strftime("%Y%m%d_%H%M%S")  # exemplo: 20250726_211503    
    
def salvar_anuncios(produtos):
    """Salva os anúncios em arquivos .txt na pasta dados/imagem"""
    criar_pasta_imagens()

    timestamp = time.strftime("%Y%m%d_%H%M%S")  # exemplo: 20250726_211503

    for i, produto in enumerate(produtos, 1):
        nome_arquivo = PASTA_IMAGENS / f"anuncio_{timestamp}_{i}.txt"
        with open(nome_arquivo, "w", encoding="utf-8") as f:
            f.write(gerar_anuncio(produto))

    print(f"💾 {len(produtos)} anúncios salvos em '{PASTA_IMAGENS}'")

def mostrar_exemplo(produto):
    """Mostra um exemplo de anúncio no console"""
    print("\n" + "═" * 50)
    print(" MODELO DE ANÚNCIO ".center(50, "═"))
    print("═" * 50 + "\n")
    print(gerar_anuncio(produto))
    print("\n" + "═" * 50)

def input_com_timeout(prompt, timeout, default):
    """Função que retorna input com valor padrão após timeout"""
    result = [default]

    def inner():
        try:
            user_input = input(prompt)
            if user_input.strip():
                result[0] = user_input
        except:
            pass

    t = threading.Thread(target=inner)
    t.daemon = True
    t.start()
    t.join(timeout)
    return result[0]

# === Execução principal ===
if __name__ == "__main__":
    try:
        with open(ARQUIVO_JSON, "r", encoding="utf-8") as f:
            produtos = json.load(f)

        if produtos:
            mostrar_exemplo(produtos[0])


            modo_automatico = "--auto" in sys.argv

            if modo_automatico:
                resposta = "s"
            else:
                resposta = input_com_timeout(
                    "\nGerar anúncios para todos os produtos? (s/n) [Padrão: s]: ",
                    5, "s"
                ).lower()

            if resposta == 's':
                salvar_anuncios(produtos)
                print("\n✅ Anúncios prontos na pasta 'dados/imagem/'!")

        else:
            print("Nenhum produto encontrado no arquivo.")
    except FileNotFoundError:
        print(f"❌ Arquivo '{ARQUIVO_JSON.name}' não encontrado em {ARQUIVO_JSON.parent}")
    except Exception as e:
        print(f"❌ Erro: {e}")
