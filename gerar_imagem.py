import os
import re
import json
import time
import requests
from pathlib import Path
from urllib.parse import urlparse

# Configurações
TENTATIVAS_MAXIMAS = 3
TEMPO_ESPERA_ERRO = 5
PASTA_IMAGENS = Path("dados/anuncios")
PASTA_IMAGENS.mkdir(parents=True, exist_ok=True)
CAMINHO_JSON = Path("dados/produtos_promocao.json")

def baixar_imagem(url_imagem, nome_arquivo):
    """Baixa e salva a imagem do produto"""
    try:
        resposta = requests.get(url_imagem, stream=True, timeout=10)
        resposta.raise_for_status()
        
        caminho_imagem = PASTA_IMAGENS / f"{nome_arquivo}.jpg"
        with open(caminho_imagem, 'wb') as f:
            for chunk in resposta.iter_content(1024):
                f.write(chunk)
        
        return caminho_imagem
    except Exception as e:
        print(f"⚠️ Erro ao baixar imagem: {e}")
        return None

def gerar_arquivos_anuncio(produto, indice):
    """Gera tanto o TXT quanto a imagem do anúncio"""
    # Gera a mensagem do anúncio
    mensagem = gerar_mensagem(produto)
    if not mensagem:
        return False
    
    # Nome base para os arquivos
    nome_base = f"anuncio_{indice}"
    
    # Salva o arquivo TXT
    caminho_txt = PASTA_IMAGENS / f"{nome_base}.txt"
    try:
        with open(caminho_txt, 'w', encoding='utf-8') as f:
            f.write(mensagem)
    except Exception as e:
        print(f"⚠️ Erro ao salvar TXT: {e}")
        return False
    
    # Se houver imagem, baixa e salva
    if produto.get('imagem'):
        caminho_imagem = baixar_imagem(produto['imagem'], nome_base)
        if not caminho_imagem:
            print("⚠️ Anúncio será criado sem imagem")
    
    return True

def gerar_mensagem(produto):
    """Gera o texto do anúncio com o formato desejado, extraindo valores do campo 'preco'"""
    try:
        nome = produto.get("nome", "Produto sem nome")
        link = produto.get("link", "#")
        preco_str = produto.get("preco", "")
        desconto = produto.get("desconto", 0)
        
        # Novas informações a serem incluídas
        vendas = produto.get("vendas")
        avaliacao = produto.get("avaliacao")

        # --- Lógica para extrair os preços ---
        # Tenta extrair o preço atual e o preço original da string
        match = re.search(r"R\$([\d\.,]+)\s+\(de\s+~?R\$([\d\.,]+)~?\)", preco_str)
        
        preco_atual = preco_str
        preco_original_linha = ""
        
        if match:
            # Caso 1: A string 'preco' já contém os dois valores. Ex: "R$29.99 (de R$90.49)"
            preco_atual = f"R${match.group(1)}"
            preco_original_linha = f"de: ~R${match.group(2)}~\n"
        elif desconto and isinstance(desconto, (int, float)) and desconto > 0:
            # Caso 2: A string 'preco' tem apenas o valor atual, mas há um desconto.
            # Calcula o preço original a partir do valor atual e do desconto.
            
            # Extrai apenas o valor numérico do preço atual
            preco_limpo = re.search(r"R\$([\d\.,]+)", preco_str)
            preco_num = float(preco_limpo.group(1).replace(",", ".")) if preco_limpo else 0.0
            
            preco_original = preco_num / (1 - desconto / 100)
            preco_original_linha = f"de: ~R${preco_original:.2f}~\n"
        
        # Monta a linha da avaliação em estrelas
        linha_avaliacao = ""
        if avaliacao and float(avaliacao) > 0:
            estrelas = int(float(avaliacao) + 0.5) # Arredonda para a estrela mais próxima
            linha_avaliacao = f"{'⭐' * estrelas} ({avaliacao})\n"

        # Monta a linha de vendas
        linha_vendas = ""
        if vendas:
            linha_vendas = f"🛒 {vendas}\n"

        # Monta a mensagem completa, usando os preços extraídos ou calculados
        return (
            f"🛍️ {nome}\n\n"
            f"{preco_original_linha}"
            f"💸 Por: {preco_atual} 🔥\n\n"
            f"{linha_avaliacao}"
            f"{linha_vendas}"
            f"👉 Link para comprar: {link}\n\n"
            f"_*Promoção sujeita a alteração a qualquer momento*_"
        )
    except Exception as e:
        print(f"⚠️ Erro ao gerar mensagem: {e}")
        return None

def main():
    try:
        # Carrega os produtos
        with open(CAMINHO_JSON, 'r', encoding='utf-8') as f:
            produtos = json.load(f)
        
        # Limpa anúncios antigos antes de começar a gerar novos
        if PASTA_IMAGENS.exists():
            for arquivo in PASTA_IMAGENS.glob('*'):
                os.remove(arquivo)
        
        # Processa cada produto
        for i, produto in enumerate(produtos, start=1):
            tentativas = 0
            sucesso = False
            
            while not sucesso and tentativas < TENTATIVAS_MAXIMAS:
                tentativas += 1
                try:
                    print(f"\n🔄 Processando produto {i} (Tentativa {tentativas}/{TENTATIVAS_MAXIMAS})")
                    
                    if gerar_arquivos_anuncio(produto, i):
                        sucesso = True
                    else:
                        raise ValueError("Falha ao gerar arquivos do anúncio")
                        
                except Exception as e:
                    print(f"⚠️ Tentativa {tentativas} falhou: {e}")
                    if tentativas < TENTATIVAS_MAXIMAS:
                        time.sleep(TEMPO_ESPERA_ERRO)
            
            if not sucesso:
                print(f"❌ Falha ao processar produto {i} após {TENTATIVAS_MAXIMAS} tentativas")

        print("\n✅ Todos os anúncios foram gerados com sucesso!")

    except Exception as e:
        print(f"\n❌ Erro crítico: {e}")
    finally:
        print("🔚 Processo finalizado")

if __name__ == "__main__":
    main()
