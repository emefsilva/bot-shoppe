import requests
import json
import time
import hashlib
import sys
from pathlib import Path
import argparse

# === CONFIGURAÇÕES ===
APP_ID = "18341780685"
APP_SECRET = "FW3M3FW3EJDVSQBLQA7FVIHEBHDEYDES"
ENDPOINT = "https://open-api.affiliate.shopee.com.br/graphql"
MAX_POR_PAGINA = 50 
DESCONTO_MINIMO = 30
MAX_PAGINAS_PARA_BUSCA = 20

# Diretório de saída
BASE_DIR = Path(__file__).parent
PASTA_SAIDA = BASE_DIR / "dados"
PASTA_SAIDA.mkdir(parents=True, exist_ok=True)
JSON_SAIDA = PASTA_SAIDA / "produtos_promocao.json"

# === FUNÇÕES ===
def gerar_signature(app_id, timestamp, payload, secret):
    texto = f"{app_id}{timestamp}{payload}{secret}"
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()

def buscar_promocoes_gerais(limite_total):
    print("🌐 Buscando promoções gerais (maior desconto)...")
    page = 1
    todos_produtos = []
    
    query = """
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
    
    while len(todos_produtos) < limite_total and page <= MAX_PAGINAS_PARA_BUSCA:
        variables = {"page": page, "limit": MAX_POR_PAGINA, "sortType": 4} # sortType 4 = Maior Desconto
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
            print(f"📦 Buscando página {page}...")
            response = requests.post(ENDPOINT, headers=headers, data=payload_json, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            if "errors" in data:
                print(f"❌ Erro na API: {data['errors']}")
                break
                
            produtos_brutos = data.get("data", {}).get("productOfferV2", {}).get("nodes", [])
            if not produtos_brutos:
                print("🚫 A página retornou vazia. Encerrando.")
                break
            
            for p in produtos_brutos:
                if p.get("sales", 0) > 0 and p.get("priceDiscountRate", 0) >= DESCONTO_MINIMO:
                    todos_produtos.append(p)
            
            page += 1
            if len(todos_produtos) >= limite_total:
                break
            time.sleep(1)
            
        except requests.exceptions.RequestException as req_error:
            print(f"❌ Erro na requisição: {req_error}")
            break
        except Exception as e:
            print(f"❌ Erro inesperado: {e}")
            break

    if len(todos_produtos) < limite_total:
        print(f"⚠️ Não foram encontrados produtos suficientes ({len(todos_produtos)}) após todas as tentativas. Encerrando.")
    
    return todos_produtos[:limite_total]


def formatar_produtos(produtos):
    produtos_formatados = []
    for p in produtos:
        try:
            preco_min = float(p.get("priceMin", 0))
            preco_max = float(p.get("priceMax", 0))
            preco_formatado = f"R${preco_min:.2f}"
            if preco_max > preco_min:
                preco_formatado += f" (de R${preco_max:.2f})"

            vendas_formatado = f"{p.get('sales', 0) // 1000}mil+ vendas" if p.get('sales', 0) >= 1000 else f"{p.get('sales', 0)}+ vendas"

            item_data = {
                "id": p.get("itemId"),
                "nome": p.get("productName", "Produto sem nome"),
                "link": p.get("offerLink", p.get("productLink", "")),
                "imagem": p.get("imageUrl", ""),
                "preco": preco_formatado,
                "desconto": p.get("priceDiscountRate", 0),
                "comissao": f"{float(p.get('commissionRate', '0')) * 100:.0f}%",
                "vendas": vendas_formatado,
                "loja": p.get("shopName", ""),
                "avaliacao": p.get("ratingStar", "0")
            }
            produtos_formatados.append(item_data)
        except Exception as format_error:
            print(f"⚠️ Erro ao formatar produto: {format_error}")
            continue
    return produtos_formatados


def salvar_produtos(produtos):
    try:
        if not produtos:
            print("⚠️ A lista de produtos está vazia. O arquivo JSON não será criado.")
            return False
            
        with open(JSON_SAIDA, "w", encoding="utf-8") as f:
            json.dump(produtos, f, indent=2, ensure_ascii=False)
        print(f"💾 Produtos salvos em {JSON_SAIDA}")
        return True
    except Exception as e:
        print(f"❌ Erro ao salvar arquivo: {e}")
        return False

def mostrar_resumo(produtos):
    print("\n📊 RESUMO DA COLETA")
    print("=" * 40)
    print(f"🔢 Total de produtos: {len(produtos)}")
    print(f"⚙️ Modo de Coleta: Promoções Gerais")
    
    if produtos:
        print(f"🏷️ Maior desconto: {max(p['desconto'] for p in produtos)}%")
        print(f"💰 Maior comissão: {max(float(p['comissao'].replace('%', '')) for p in produtos)}%")
        print(f"🛒 Loja com mais produtos: {max(set(p['loja'] for p in produtos), key=lambda x: sum(1 for p in produtos if p['loja'] == x))}")
    print("=" * 40)

# === EXECUÇÃO PRINCIPAL ===
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Coleta produtos da API da Shopee.")
    parser.add_argument("limite", nargs="?", type=int, default=100, help="Quantidade de produtos a buscar.")
    args = parser.parse_args()

    try:
        limite = args.limite
        
        produtos_brutos = buscar_promocoes_gerais(limite_total=limite)
        produtos_formatados = formatar_produtos(produtos_brutos)

        if produtos_formatados and salvar_produtos(produtos_formatados):
            mostrar_resumo(produtos_formatados)
        else:
            print("❌ Nenhum produto encontrado ou erro ao salvar os produtos.")

    except ValueError:
        print("Por favor, digite um número válido.")
    except KeyboardInterrupt:
        print("\nOperação cancelada pelo usuário")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")