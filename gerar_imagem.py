import json
from datetime import datetime
import os
import threading

def criar_pasta_imagens():
    """Cria a pasta 'imagem' se não existir"""
    if not os.path.exists('imagem'):
        os.makedirs('imagem')
        print("📂 Pasta 'imagem' criada com sucesso!")

def gerar_anuncio(produto):
    """Gera um anúncio com emojis e formatação melhorada"""
    # Extrai o preço atual e original
    preco_atual = produto['preco'].split(' ')[0]  # Pega o primeiro valor (R$XX.XX)
    preco_original = produto['preco'].split('de ')[1].replace(')', '') if 'de' in produto['preco'] else ''
    
    # Formata o anúncio com emojis
    anuncio = (
        f"🛍️ {produto['nome']}\n"
        f"\n"
    )
    
    if preco_original:
        anuncio += f"de: ~{preco_original}~\n"
    
    anuncio += (
        f"💸 Por: {preco_atual} 🔥\n"
       # f"{produto['vendas']}\n"
       # f"Avaliação: {produto['avaliacao']} ⭐ \n\n"
        f"\n"
        f"👉 Link para comprar: {produto['link']}\n"
        f"\n"
        f"_*Promoção sujeita a alteração a qualquer momento*_\n" 
    )
    
    return anuncio

def salvar_anuncios(produtos):
    """Salva todos os anúncios em arquivos na pasta 'imagem'"""
    criar_pasta_imagens()
    
    for i, produto in enumerate(produtos, 1):
        nome_arquivo = f"imagem/anuncio_{i}.txt"
        with open(nome_arquivo, "w", encoding="utf-8") as f:
            f.write(gerar_anuncio(produto))
    
    print(f"💾 {len(produtos)} anúncios salvos na pasta 'imagem'")

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

# Carrega os produtos
try:
    with open("produtos_promocao.json", "r", encoding="utf-8") as f:
        produtos = json.load(f)
    
    if produtos:
        mostrar_exemplo(produtos[0])
        resposta = input_com_timeout("\nGerar anúncios para todos os produtos? (s/n) [Padrão: s]: ", 5, "s").lower()
        if resposta == 's':
            salvar_anuncios(produtos)
            print("\n✅ Anúncios prontos na pasta 'imagem'!")
    else:
        print("Nenhum produto encontrado no arquivo.")

except FileNotFoundError:
    print("❌ Arquivo 'produtos_promocao.json' não encontrado")
except Exception as e:
    print(f"❌ Erro: {e}")