# gerar_imagem.py

import os
import re
import requests
from pathlib import Path
from typing import List, Dict, Optional
import sys
import time

# === CONFIGURAÇÕES GERAIS ===
PASTA_ANUNCIOS = Path("dados/anuncios")
PASTA_ANUNCIOS.mkdir(parents=True, exist_ok=True)
API_URL = "http://localhost:8000"
TENTATIVAS_MAXIMAS = 3
TEMPO_ESPERA_ERRO = 5


# === PAINEL DE CONTROLE ESTRATÉGICO ===
# Defina aqui a sua estratégia para a geração de hoje
ESTRATEGIA_DO_DIA = "vendas" # "vendas" ou "padrao"
CATEGORIAS_DO_DIA = ["Casa e Decoração", "Moda Feminina"] # Deixe None para não filtrar
QUANTIDADE_A_GERAR = 50
# ======================================

# === FUNÇÕES DE COMUNICAÇÃO E ARQUIVOS ===
def obter_produtos_da_api(
    quantidade: int,
    estrategia: str,
    categorias: Optional[List[str]] = None
):
    """
    Busca produtos da API, aplicando filtros de ordenação e categoria.
    """
    print(f"🌐 Buscando {quantidade} produtos da API...")
    print(f"   - Estratégia: {estrategia.upper()}")
    if categorias:
        print(f"   - Categorias: {', '.join(categorias)}")
        
    try:
        # Monta os parâmetros de forma segura para a URL
        params = {
            "quantidade": quantidade,
            "ordenar_por": estrategia
        }
        # Adiciona a lista de categorias se ela for fornecida
        if categorias:
            params["categoria"] = categorias

        endpoint = f"{API_URL}/api/lote-produtos"
        
        # A biblioteca 'requests' lida com a formatação da lista na URL
        response = requests.get(endpoint, params=params, timeout=30)
        
        response.raise_for_status()
        produtos = response.json()
        print(f"✅ {len(produtos)} produtos recebidos.")
        return produtos
    except requests.RequestException as e:
        print(f"❌ Erro ao conectar com a API: {e}")
        return []

def baixar_imagem(url_imagem, nome_arquivo):
    try:
        resposta = requests.get(url_imagem, stream=True, timeout=10)
        resposta.raise_for_status()
        caminho_imagem = PASTA_ANUNCIOS / f"{nome_arquivo}.jpg"
        with open(caminho_imagem, 'wb') as f:
            for chunk in resposta.iter_content(1024): f.write(chunk)
        return caminho_imagem
    except Exception as e:
        print(f"⚠️ Erro ao baixar imagem: {e}"); return None

def gerar_mensagem(produto):
    try:
        nome = produto.get("nome", "Produto sem nome"); link = produto.get("link", "#"); preco_str = produto.get("preco", ""); desconto = produto.get("desconto", 0); vendas = produto.get("vendas"); avaliacao = produto.get("avaliacao")
        preco_atual = preco_str; preco_original_linha = ""
        match = re.search(r"R\$([\d\.,]+)\s+\(de\s+R\$([\d\.,]+)\)", preco_str)
        if match:
            preco_atual = f"R${match.group(1)}"; preco_original_linha = f"de: ~R${match.group(2)}~\n"
        elif desconto > 0:
            preco_limpo_match = re.search(r"R\$([\d\.,]+)", preco_str)
            if preco_limpo_match:
                preco_num = float(preco_limpo_match.group(1).replace(",", ".")); preco_original = preco_num / (1 - (desconto / 100)); preco_original_linha = f"de: ~R${preco_original:,.2f}~\n".replace(",", "X").replace(".", ",").replace("X", ".")
        linha_avaliacao = ""
        if avaliacao and float(avaliacao) > 0:
            estrelas = '⭐' * int(float(avaliacao) + 0.5); linha_avaliacao = f"{estrelas} ({avaliacao})\n"
        linha_vendas = f"🛒 {vendas}\n" if vendas else ""
        return (f"🛍️ {nome}\n\n{preco_original_linha}💸 Por: {preco_atual} 🔥\n\n{linha_avaliacao}{linha_vendas}👉 Link para comprar: {link}\n\n_*Promoção sujeita a alteração a qualquer momento*_")
    except Exception as e:
        print(f"⚠️ Erro ao gerar mensagem para o produto {produto.get('id')}: {e}"); return None

def gerar_arquivos_anuncio(produto, indice):
    mensagem = gerar_mensagem(produto)
    if not mensagem: return False
    nome_base = f"anuncio_{indice}_{produto['id']}"
    caminho_txt = PASTA_ANUNCIOS / f"{nome_base}.txt"
    with open(caminho_txt, 'w', encoding='utf-8') as f: f.write(mensagem)
    if produto.get('imagem'): baixar_imagem(produto['imagem'], nome_base)
    return True

# === FUNÇÃO PRINCIPAL ===
def main():
    """Função principal que orquestra a GERAÇÃO EM MASSA com estratégia e filtros."""
    
    # Chama a API com as suas escolhas estratégicas
    produtos_para_gerar = obter_produtos_da_api(
        quantidade=QUANTIDADE_A_GERAR,
        estrategia=ESTRATEGIA_DO_DIA,
        categorias=CATEGORIAS_DO_DIA
    )
    
    if not produtos_para_gerar: 
        print("❌ Nenhum produto encontrado com os critérios definidos. Encerrando.")
        return

    if PASTA_ANUNCIOS.exists():
        print(f"🧹 Limpando a pasta '{PASTA_ANUNCIOS}' antes de gerar os novos anúncios...")
        for arquivo in PASTA_ANUNCIOS.glob('*'): os.remove(arquivo)

    print(f"\n✍️ Gerando arquivos para {len(produtos_para_gerar)} produtos...")
    sucessos, falhas = 0, 0
    for i, produto in enumerate(produtos_para_gerar, start=1):
        tentativas = 0
        sucesso_produto = False
        while not sucesso_produto and tentativas < TENTATIVAS_MAXIMAS:
            try:
                print(f" -> Processando anúncio {i}/{len(produtos_para_gerar)}: {produto['nome'][:30]}... (Tentativa {tentativas + 1})")
                if gerar_arquivos_anuncio(produto, i):
                    sucesso_produto = True; sucessos += 1
                else:
                    raise ValueError("Falha na geração dos arquivos do anúncio")
            except Exception as e:
                tentativas += 1; print(f"   ⚠️ Erro: {e}")
                if tentativas < TENTATIVAS_MAXIMAS: time.sleep(TEMPO_ESPERA_ERRO)
        
        if not sucesso_produto:
            falhas += 1; print(f"   ❌ Falha definitiva ao processar o produto {produto['id']}.")

    print(f"\n✅ Geração concluída. Sucessos: {sucessos}, Falhas: {falhas}")

if __name__ == "__main__":
    main()