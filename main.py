# Importa as bibliotecas necessárias
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import requests
import json
import uvicorn
import time
import hashlib
import os
from typing import List, Optional

# Configurações do FastAPI
app = FastAPI(
    title="API de Busca de Produtos da Shopee",
    description="API centralizada para buscar e filtrar produtos da Shopee através da API de Afiliados.",
    version="1.0.0"
)

# A sua chave de API e ID do aplicativo da Shopee.
SHOPEE_APP_ID = "18341780685"
SHOPEE_APP_SECRET = "FW3M3FW3EJDVSQBLQA7FVIHEBHDEYDES"
SHOPEE_API_URL = "https://open-api.affiliate.shopee.com.br/graphql"
SHOPEE_REST_API_URL = "https://open-api.affiliate.shopee.com.br/api/v2"

# === FUNÇÕES DE LÓGICA DE NEGÓCIO ===

def gerar_signature(app_id: str, timestamp: int, payload: str, secret: str) -> str:
    """
    Gera a assinatura SHA256 necessária para a autenticação GraphQL.
    """
    texto = f"{app_id}{timestamp}{payload}{secret}"
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()

def gerar_rest_signature(app_id: str, path: str, timestamp: int, secret: str) -> str:
    """
    Gera a assinatura HMAC-SHA256 para a API REST da Shopee.
    """
    texto = f"{app_id}{path}{timestamp}{secret}"
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()

def fetch_from_shopee_graphql(query: str, variables: dict = {}) -> dict:
    """
    Faz uma requisição GraphQL para a API da Shopee com autenticação SHA256.
    """
    try:
        payload = {"query": query, "variables": variables}
        payload_json = json.dumps(payload, separators=(',', ':'))
        timestamp = int(time.time())
        signature = gerar_signature(SHOPEE_APP_ID, timestamp, payload_json, SHOPEE_APP_SECRET)

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"SHA256 Credential={SHOPEE_APP_ID}, Timestamp={timestamp}, Signature={signature}",
            "User-Agent": "Mozilla/5.0"
        }

        response = requests.post(SHOPEE_API_URL, headers=headers, data=payload_json, timeout=15)
        response.raise_for_status()

        data = response.json()

        if "errors" in data:
            print(f"❌ Erro na API GraphQL: {data['errors']}")
            raise Exception(f"Erro na API GraphQL da Shopee: {data['errors']}")

        if 'data' in data:
            return data['data']
        else:
            print("Erro na resposta da API GraphQL da Shopee:", data)
            raise Exception("Erro na resposta da API GraphQL da Shopee")

    except requests.exceptions.RequestException as e:
        print(f"❌ Erro de requisição para a API GraphQL da Shopee: {e}")
        raise HTTPException(status_code=500, detail=f"Erro de comunicação com a API GraphQL da Shopee: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def fetch_from_shopee_rest_api(path: str, params: dict = {}) -> dict:
    """
    Faz uma requisição para a API REST da Shopee com autenticação HMAC-SHA256.
    """
    try:
        timestamp = int(time.time())
        signature = gerar_rest_signature(SHOPEE_APP_ID, path, timestamp, SHOPEE_APP_SECRET)

        full_url = f"{SHOPEE_REST_API_URL}{path}"
        
        # Adiciona os parâmetros de autenticação
        params.update({
            "partner_id": SHOPEE_APP_ID,
            "timestamp": timestamp,
            "sign": signature,
        })
        
        response = requests.get(full_url, params=params, timeout=15)
        response.raise_for_status()

        data = response.json()

        if data.get("error"):
            print(f"❌ Erro na API REST: {data['error']} - {data.get('message')}")
            raise Exception(f"Erro na API REST da Shopee: {data.get('message')}")

        if 'response' in data:
            return data['response']
        else:
            print("Erro na resposta da API REST da Shopee:", data)
            raise Exception("Erro na resposta da API REST da Shopee")
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro de requisição para a API REST da Shopee: {e}")
        raise HTTPException(status_code=500, detail=f"Erro de comunicação com a API REST da Shopee: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def formatar_produtos(produtos: list) -> list:
    """
    Formata a lista de produtos brutos retornados pela API da Shopee.
    """
    produtos_formatados = []
    for p in produtos:
        try:
            preco_min = float(p.get("priceMin", 0))
            preco_max = float(p.get("priceMax", 0))
            preco_formatado = f"R${preco_min:.2f}"
            if preco_max > preco_min:
                preco_formatado += f" - R${preco_max:.2f}"

            vendas = p.get('sales', 0)
            vendas_formatado = f"{vendas // 1000}mil+ vendas" if vendas >= 1000 else f"{vendas}+ vendas"

            item_data = {
                "id": str(p.get("itemId", "")),
                "nome": p.get("productName", "Produto sem nome"),
                "link": p.get("offerLink", p.get("productLink", "")),
                "imagem": p.get("imageUrl", ""),
                "preco": preco_formatado,
                "desconto": int(p.get("priceDiscountRate", 0)),
                "comissao": f"{float(p.get('commissionRate', '0')) * 100:.0f}%",
                "vendas": vendas_formatado,
                "loja": p.get("shopName", ""),
                "avaliacao": float(p.get("ratingStar", "0"))
            }
            produtos_formatados.append(item_data)
        except Exception as format_error:
            print(f"⚠️ Erro ao formatar produto: {format_error}")
            continue
    return produtos_formatados

# --- MODELOS DE DADOS (Pydantic) ---
class Product(BaseModel):
    id: str
    nome: str
    link: str
    imagem: str
    preco: str
    desconto: int
    comissao: str
    vendas: str
    loja: str
    avaliacao: float

class ProductListResponse(BaseModel):
    total: int
    items: List[Product]
    page_number: int
    page_size: int
    
class Category(BaseModel):
    category_id: int
    parent_category_id: int
    original_category_name: str
    display_category_name: str
    has_children: bool

class CategoryListResponse(BaseModel):
    category_list: List[Category]

# --- ENDPOINTS DA SUA API ---

SHOPEE_PRODUCT_OFFER_QUERY = """
query productOfferV2($page: Int!, $limit: Int!, $sortType: Int) {
  productOfferV2(page: $page, limit: $limit, sortType: $sortType) {
    nodes {
      itemId
      productName
      productLink
      offerLink
      imageUrl
      commissionRate
      priceMin
      priceMax
      sales
      priceDiscountRate
      shopName
      ratingStar
    }
  }
}
"""

@app.get("/api/promocoes/tudo", response_model=List[Product])
def buscar_todas_promocoes(
    limite: int = Query(100, ge=1, le=500, description="Quantidade total de produtos a buscar.")
):
    """
    Retorna uma lista extensa de produtos em promoção, buscando múltiplas páginas.
    """
    page = 1
    produtos_brutos = []
    max_por_pagina = 50
    
    while len(produtos_brutos) < limite:
        variables = {"page": page, "limit": max_por_pagina, "sortType": 4}
        try:
            shopee_data = fetch_from_shopee_graphql(SHOPEE_PRODUCT_OFFER_QUERY, variables)
            novos_produtos = shopee_data.get("productOfferV2", {}).get("nodes", [])
            
            if not novos_produtos:
                break
                
            produtos_brutos.extend(novos_produtos)
            page += 1
            time.sleep(1)

        except HTTPException:
            break

    produtos_brutos = produtos_brutos[:limite]
    return formatar_produtos(produtos_brutos)


@app.get("/api/promocoes/paginado", response_model=ProductListResponse)
def listar_promocoes_paginado(
    page: int = Query(1, ge=1, description="Número da página de resultados"),
    limit: int = Query(50, ge=1, le=50, description="Número de itens por página")
):
    """
    Retorna uma lista paginada de produtos em promoção com maior desconto.
    """
    variables = {"page": page, "limit": limit, "sortType": 4}
    shopee_data = fetch_from_shopee_graphql(SHOPEE_PRODUCT_OFFER_QUERY, variables)
    
    produtos_brutos = shopee_data.get("productOfferV2", {}).get("nodes", [])
    
    # A API não fornece o total exato, então estimamos.
    total_estimado = (page * limit) + (len(produtos_brutos) if len(produtos_brutos) == limit else 0)
    
    return ProductListResponse(
        total=total_estimado,
        items=formatar_produtos(produtos_brutos),
        page_number=page,
        page_size=limit
    )

@app.get("/api/categorias", response_model=CategoryListResponse)
def listar_categorias(
    language: str = Query("pt-br", description="Linguagem da categoria (ex: en, zh-Hant, pt-br)")
):
    """
    Retorna uma lista de categorias de produtos da Shopee.
    Este endpoint utiliza a API REST da Shopee Open Platform.
    """
    path = "/product/get_category"
    params = {"language": language}
    
    shopee_data = fetch_from_shopee_rest_api(path, params)
    
    return CategoryListResponse(category_list=shopee_data.get("category_list", []))


@app.get("/api/produtos/busca", response_model=ProductListResponse)
def buscar_produtos_por_termo(
    termo: str = Query(..., min_length=3, description="Termo de busca para o produto"),
    page: int = Query(1, ge=1, description="Número da página de resultados"),
    limit: int = Query(50, ge=1, le=50, description="Número de itens a retornar")
):
    """
    Busca produtos utilizando um termo, buscando em várias páginas e filtrando os resultados.
    A API da Shopee de Afiliados não oferece um endpoint de busca global com paginação,
    então a melhor abordagem é buscar múltiplos lotes de produtos e filtrar localmente.
    """
    produtos_brutos = []
    pagina_api = 1
    # Aumentando o limite de páginas para buscar para aumentar a quantidade de resultados
    max_paginas_para_buscar = 50

    # A busca aqui é feita em várias páginas de ofertas para aumentar o número de resultados
    while pagina_api <= max_paginas_para_buscar:
        variables = {"page": pagina_api, "limit": 50, "sortType": 0} # SortType 0 é por Relevância
        try:
            shopee_data = fetch_from_shopee_graphql(SHOPEE_PRODUCT_OFFER_QUERY, variables)
            novos_produtos = shopee_data.get("productOfferV2", {}).get("nodes", [])
            
            if not novos_produtos:
                break
                
            produtos_brutos.extend(novos_produtos)
            pagina_api += 1
            time.sleep(0.5) # Pausa para evitar exceder o limite de requisições
        except HTTPException:
            break
    
    # Filtra os produtos obtidos para encontrar os que correspondem ao termo de busca
    termo_lower = termo.lower()
    produtos_filtrados = [
        p for p in produtos_brutos 
        if p.get("productName", "").lower().find(termo_lower) != -1
    ]

    # Pagina os resultados filtrados
    inicio = (page - 1) * limit
    fim = inicio + limit
    produtos_paginados = produtos_filtrados[inicio:fim]

    return ProductListResponse(
        total=len(produtos_filtrados),
        items=formatar_produtos(produtos_paginados),
        page_number=page,
        page_size=limit
    )

# Executa o servidor quando o arquivo é rodado
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
