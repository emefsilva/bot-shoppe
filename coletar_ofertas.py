import requests
import json
import time
import hashlib
import threading
import sys
from pathlib import Path

# === CONFIGURAÇÕES ===
APP_ID = "18341780685"
APP_SECRET = "FW3M3FW3EJDVSQBLQA7FVIHEBHDEYDES"
ENDPOINT = "https://open-api.affiliate.shopee.com.br/graphql"
MAX_POR_PAGINA = 20

# Diretório de saída
BASE_DIR = Path(__file__).parent
PASTA_SAIDA = BASE_DIR / "dados"
PASTA_SAIDA.mkdir(parents=True, exist_ok=True)
JSON_SAIDA = PASTA_SAIDA / "produtos_promocao.json"

# === FUNÇÕES ===
def gerar_signature(app_id, timestamp, payload, secret):
    texto = f"{app_id}{timestamp}{payload}{secret}"
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()

def input_com_timeout(prompt, timeout, default):
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

def buscar_produtos_paginados(limite_total=100):
    page = 1
    todos_produtos = []
    limite_por_requisicao = min(MAX_POR_PAGINA, limite_total)

    while len(todos_produtos) < limite_total:
        query = """
        query productOfferV2($page: Int!, $limit: Int!) {
          productOfferV2(page: $page, limit: $limit, sortType: 2) {
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
            pageInfo {
              hasNextPage
            }
          }
        }
        """

        variables = {"page": page, "limit": limite_por_requisicao}
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
            print(f"📦 Buscando página {page} ({(page - 1) * limite_por_requisicao + 1}-{page * limite_por_requisicao})...")
            response = requests.post(ENDPOINT, headers=headers, data=payload_json, timeout=15)
            response.raise_for_status()
            data = response.json()

            if "errors" in data:
                print(f"❌ Erro na API: {data['errors']}")
                break

            produtos = data.get("data", {}).get("productOfferV2", {}).get("nodes", [])
            if not produtos:
                print("🚫 Nenhum produto retornado. Encerrando.")
                break

            produtos_antes = len(todos_produtos)

            for p in produtos:
                try:
                    vendas = p.get("sales", 0)
                    if vendas == 0:
                        continue

                    preco_min = float(p.get("priceMin", 0))
                    preco_max = float(p.get("priceMax", 0))
                    preco_formatado = f"R${preco_min:.2f}"
                    if preco_max > preco_min:
                        preco_formatado += f" (de R${preco_max:.2f})"

                    vendas_formatado = f"{vendas // 1000}mil+ vendas" if vendas >= 1000 else f"{vendas}+ vendas"

                    todos_produtos.append({
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
                    })
                except Exception as format_error:
                    print(f"⚠️ Erro ao formatar produto: {format_error}")
                    continue

            if len(todos_produtos) == produtos_antes:
                print("🚫 Nenhum novo produto adicionado. Encerrando.")
                break

            if not data.get("data", {}).get("productOfferV2", {}).get("pageInfo", {}).get("hasNextPage", False):
                print("🚫 Última página alcançada.")
                break

            if len(todos_produtos) >= limite_total:
                break

            page += 1
            time.sleep(1)

        except requests.exceptions.RequestException as req_error:
            print(f"❌ Erro na requisição: {req_error}")
            break
        except json.JSONDecodeError as json_error:
            print(f"❌ Erro ao decodificar JSON: {json_error}")
            break
        except Exception as e:
            print(f"❌ Erro inesperado: {e}")
            break

    return todos_produtos[:limite_total]

def salvar_produtos(produtos):
    try:
        with open(JSON_SAIDA, "w", encoding="utf-8") as f:
            json.dump(produtos, f, indent=2, ensure_ascii=False)
        print(f"💾 Produtos salvos em {JSON_SAIDA}")
    except Exception as e:
        print(f"❌ Erro ao salvar arquivo: {e}")

def mostrar_resumo(produtos):
    print("\n📊 RESUMO DA COLETA")
    print("=" * 40)
    print(f"🔢 Total de produtos: {len(produtos)}")
    if produtos:
        print(f"🏷️ Maior desconto: {max(p['desconto'] for p in produtos)}%")
        print(f"💰 Maior comissão: {max(float(p['comissao'].replace('%', '')) for p in produtos)}%")
        print(f"🛒 Loja com mais produtos: {max(set(p['loja'] for p in produtos), key=lambda x: sum(1 for p in produtos if p['loja'] == x))}")
    print("=" * 40)

# === EXECUÇÃO PRINCIPAL ===
if __name__ == "__main__":
    try:
        modo_automatico = "--auto" in sys.argv
        qtd_arg = next((arg for arg in sys.argv if arg.isdigit()), None)

        if modo_automatico:
            entrada = qtd_arg or "100"
        elif sys.stdin.isatty():
            entrada = input("Quantos produtos deseja buscar? (20-2000) [Padrão: 20]: ") or "20"
        else:
            entrada = "20"

        limite = max(20, min(2000, int(entrada)))

        produtos = buscar_produtos_paginados(limite_total=limite)

        if produtos:
            salvar_produtos(produtos)
            mostrar_resumo(produtos)

            if not modo_automatico and sys.stdin.isatty():
                ver_detalhes = input_com_timeout("Deseja ver os detalhes dos produtos? (s/n) [Padrão: n]: ", 5, "n").lower()
                if ver_detalhes == 's':
                    for i, p in enumerate(produtos[:10], 1):
                        print(f"\n{i}. {p['nome']}")
                        print(f"   Preço: {p['preco']} | Desconto: {p['desconto']}%")
                        print(f"   Vendas: {p['vendas']} | Comissão: {p['comissao']}")
                        print(f"   Loja: {p['loja']} | Avaliação: {p['avaliacao']}")
        else:
            print("❌ Nenhum produto encontrado ou erro ao consultar a API.")

    except ValueError:
        print("Por favor, digite um número válido.")
    except KeyboardInterrupt:
        print("\nOperação cancelada pelo usuário")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
