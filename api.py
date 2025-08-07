# api.py

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Dict
import requests
import json
import time
import uuid
import hashlib
from pathlib import Path
from datetime import datetime
import sqlite3
from enum import Enum
from typing import List, Dict, Optional

# === CONFIGURAÇÃO INICIAL ===
app = FastAPI(
    title="API Estratégica de Ofertas Shopee",
    description="Coleta ofertas e as entrega de forma ordenada por diferentes estratégias.",
    version="4.0",
    docs_url="/docs",
    redoc_url=None,
)

# === CONSTANTES E DIRETÓRIOS ===
SHOPEE_APP_ID = "18341780685"
SHOPEE_APP_SECRET = "FW3M3FW3EJDVSQBLQA7FVIHEBHDEYDES"
SHOPEE_API_URL = "https://open-api.affiliate.shopee.com.br/graphql"

DATA_DIR = Path("dados")
DATA_DIR.mkdir(exist_ok=True)
DB_FILE = DATA_DIR / "shopee_offers.db"

# === SETUP DO BANCO DE DADOS ===
def init_db():
    """Cria/Atualiza a tabela do banco de dados para incluir a coluna de vendas brutas."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Cria a tabela se não existir
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id TEXT PRIMARY KEY, 
            nome TEXT NOT NULL, 
            link TEXT,
            imagem TEXT,
            preco TEXT, 
            desconto INTEGER,
            vendas TEXT,
            vendas_raw INTEGER,
            avaliacao TEXT, 
            loja TEXT,
            categoria TEXT,
            is_sent BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Garante que a coluna 'vendas_raw' exista, para compatibilidade com bancos antigos
    try:
       # cursor.execute("ALTER TABLE products ADD COLUMN vendas_raw INTEGER;")
        cursor.execute("ALTER TABLE products ADD COLUMN categoria TEXT;")
    except sqlite3.OperationalError:
        pass # Coluna já existe

    conn.commit()
    conn.close()

@app.on_event("startup")
async def startup_event():
    init_db()

# === MODELOS (Enum e Pydantic) ===
class TipoOrdenacao(str, Enum):
    padrao = "padrao"
    vendas = "vendas"

class FormattedProduct(BaseModel):
    id: str; nome: str; link: str; imagem: str; preco: str; desconto: int; vendas: str; vendas_raw: int; avaliacao: str; loja: str

class ConfirmacaoEnvio(BaseModel):
    item_id: str = Field(..., alias="itemId"); sent_at: datetime

# === FUNÇÕES AUXILIARES ===
def categorizar_produto(nome_produto: str) -> str:
    """Analisa o nome de um produto e retorna uma categoria baseada em palavras-chave."""
    nome_lower = nome_produto.lower()
    
    # Você pode expandir esta lista com quantas palavras-chave quiser!
    categorias = {
        "Casa e Decoração": ["panela", "organizador", "lençol", "cozinha", "decoração", "banheiro", "rodo", "esfregão", "mesa", "vaso"],
        "Moda Feminina": ["vestido", "saia", "batom", "maquiagem", "sutiã", "calça feminina", "sandália", "bolsa"],
        "Eletrônicos": ["fone", "carregador", "power bank", "smartwatch", "cabo", "celular", "tablet", "notebook"],
        "Pet": ["coleira", "gato", "cachorro", "comedouro", "brinquedo pet", "arranhador", "gaiola"]
    }
    
    for categoria, palavras_chave in categorias.items():
        for palavra in palavras_chave:
            if palavra in nome_lower:
                return categoria
                
    return "Outros" # Categoria padrão se nenhuma palavra-chave for encontrada

def gerar_signature(app_id: str, timestamp: int, payload: str, secret: str) -> str:
    texto = f"{app_id}{timestamp}{payload}{secret}"; return hashlib.sha256(texto.encode("utf-8")).hexdigest()

def fetch_from_shopee(page: int, limit: int = 50) -> List[Dict]:
    # Por padrão, a coleta sempre busca pelos maiores descontos (sortType: 4)
    query = """ query productOfferV2($page: Int!, $limit: Int!, $sortType: Int) { productOfferV2(page: $page, limit: $limit, sortType: $sortType) { nodes { itemId productName productLink offerLink imageUrl priceMin priceMax sales priceDiscountRate shopName ratingStar } } } """
    payload = {"query": query,"variables": {"page": page, "limit": limit, "sortType": 4}}
    payload_json = json.dumps(payload, separators=(',', ':'))
    timestamp = int(time.time()); signature = gerar_signature(SHOPEE_APP_ID, timestamp, payload_json, SHOPEE_APP_SECRET)
    headers = {"Content-Type": "application/json","Authorization": f"SHA256 Credential={SHOPEE_APP_ID}, Timestamp={timestamp}, Signature={signature}",}
    response = requests.post(SHOPEE_API_URL, headers=headers, data=payload_json, timeout=15)
    response.raise_for_status(); data = response.json()
    if "errors" in data: raise HTTPException(status_code=500, detail=f"Erro na API da Shopee: {data['errors']}")
    return data.get("data", {}).get("productOfferV2", {}).get("nodes", [])

def formatar_produtos_para_banco(produtos_brutos: List[Dict]) -> List[Dict]:
    produtos_formatados = []
    for p in produtos_brutos:
        try:
            vendas_raw = int(p.get('sales', 0))
            vendas_formatado = f"{vendas_raw // 1000}mil+ vendas" if vendas_raw >= 1000 else f"{vendas_raw}+ vendas"
            preco_min = float(p.get("priceMin", 0)); preco_max = float(p.get("priceMax", 0))
            preco_formatado = f"R${preco_min:.2f}".replace('.', ',')
            if preco_max > preco_min: preco_formatado += f" (de R${preco_max:.2f})".replace('.', ',')
            nome_produto = p.get("productName", "")
            categoria_produto = categorizar_produto(nome_produto)
            
            item_data = {
                "id": str(p.get("itemId")),
                "nome": p.get("productName", "Produto sem nome"),
                "link": p.get("offerLink", p.get("productLink", "")),
                "imagem": p.get("imageUrl", ""),
                "preco": preco_formatado, "desconto": int(p.get("priceDiscountRate", 0)),
                "vendas": vendas_formatado, 
                "vendas_raw": vendas_raw,
                "avaliacao": str(p.get("ratingStar", "0")), 
                "loja": p.get("shopName", ""),
                "categoria": categoria_produto
            }
            produtos_formatados.append(item_data)
        except Exception as e:
            print(f"⚠️ Erro ao formatar produto {p.get('itemId')}: {e}")
            continue
    return produtos_formatados

# === ENDPOINTS PRINCIPAIS ===

@app.post("/api/iniciar-coleta", tags=["1. Controle do Bot"])
def iniciar_coleta_diaria(paginas: int = Query(50, ge=1, le=200), desconto_minimo: int = Query(30, ge=0, le=100)):
    
    todos_produtos_brutos = []
    
    for pagina in range(1, paginas + 1):
        try:
            produtos_pagina = fetch_from_shopee(pagina)
            if not produtos_pagina: break
            for p in produtos_pagina:
                if p.get("sales", 0) > 0 and p.get("priceDiscountRate", 0) >= desconto_minimo:
                    todos_produtos_brutos.append(p)
            time.sleep(1)
        except Exception as e: print(f"❌ Erro ao buscar página {pagina}: {e}"); break
    
    produtos_prontos = formatar_produtos_para_banco(todos_produtos_brutos)
    
    conn = sqlite3.connect(DB_FILE); cursor = conn.cursor()

    produtos_inseridos = 0
    
    for produto in produtos_prontos:
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO products (id, nome, link, imagem, preco, desconto, vendas, vendas_raw, avaliacao, loja, categoria)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                produto['id'],
                produto['nome'],
                produto['link'],
                produto['imagem'], 
                produto['preco'], 
                produto['desconto'],
                produto['vendas'],
                produto['vendas_raw'], 
                produto['avaliacao'], 
                produto['loja'],
                produto['categoria'] # <<< Agora dentro do parêntese
            ))
            
            if cursor.rowcount > 0:
                produtos_inseridos += 1
        
        except Exception as e:
            print(f"Erro ao inserir produto {produto['id']}: {e}")

    conn.commit()
    conn.close()

    return {"status": "coleta_concluida", "produtos_recebidos": len(produtos_prontos), "novos_produtos_adicionados": produtos_inseridos}

@app.get("/api/lote-produtos", response_model=List[FormattedProduct], tags=["2. Geração de Anúncios"])
def obter_lote_produtos(
    quantidade: int = Query(50, ge=1, le=200),
    ordenar_por: TipoOrdenacao = Query(TipoOrdenacao.padrao),
    categoria: Optional[List[str]] = Query(None, description="Liste as categorias para filtrar")
):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    params = []
    query = "SELECT * FROM products WHERE is_sent = FALSE"
    
    if categoria:
        placeholders = ', '.join('?' for _ in categoria)
        query += f" AND categoria IN ({placeholders})"
        params.extend(categoria)
    
    if ordenar_por.value == "vendas":
        query += " ORDER BY vendas_raw DESC"
    
    query += " LIMIT ?"
    params.append(quantidade)
    
    cursor.execute(query, tuple(params))
    produtos = [dict(row) for row in cursor.fetchall()]
    
    conn.close() # <<< DETALHE ADICIONADO: Fechando a conexão.
    
    return produtos

@app.post("/api/registrar-envios", tags=["3. Envio WhatsApp"])
def registrar_envios(items: List[ConfirmacaoEnvio]):
    conn = sqlite3.connect(DB_FILE); cursor = conn.cursor()
    ids_para_marcar = [item.item_id for item in items]
    cursor.executemany("UPDATE products SET is_sent = TRUE WHERE id = ?", [(id,) for id in ids_para_marcar])
    conn.commit(); updates_reais = conn.total_changes; conn.close()
    return {"status": "envios_registrados", "items_marcados_como_enviados": updates_reais}

@app.get("/api/status/geral", tags=["4. Monitoramento"])
def status_geral():
    conn = sqlite3.connect(DB_FILE); cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*), SUM(CASE WHEN is_sent = TRUE THEN 1 ELSE 0 END) FROM products")
    total, enviados = cursor.fetchone(); conn.close()
    enviados = enviados or 0
    return {"total_produtos_na_base": total, "total_enviados": enviados, "total_nao_enviados": total - enviados}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True, reload_exclude="dados")