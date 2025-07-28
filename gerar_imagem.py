import os
import re
import json
import requests
from pathlib import Path

PASTA_IMAGENS = Path(__file__).parent / "dados" / "imagem"
PASTA_IMAGENS.mkdir(parents=True, exist_ok=True)

with open("produtos_promocao.json", "r", encoding="utf-8") as f:
    produtos = json.load(f)

for i, produto in enumerate(produtos):
    nome = produto["nome"]
    link = produto["link"]
    imagem_url = produto["imagem"]
    preco = produto["preco"]
    desconto = produto.get("desconto", 0)

    # 🧼 Limpar preço atual (pegar apenas o número)
    preco_limpo = re.search(r"\d+(?:[\.,]\d+)?", preco)
    preco_num = float(preco_limpo.group().replace(",", ".")) if preco_limpo else 0.0

    # 💰 Calcular preço original se houver desconto
    if desconto:
        preco_original = preco_num / (1 - desconto / 100)
        linha_de = f"de: ~R${preco_original:.2f}~\n"
    else:
        linha_de = ""

    # ✍️ Montar a mensagem
    mensagem = (
        f"🛍️ {nome}\n\n"
        f"{linha_de}"
        f"💸 Por: R${preco_num:.2f} 🔥\n\n"
        f"👉 Link para comprar: {link}\n\n"
        f"_*Promoção sujeita a alteração a qualquer momento*_"
    )

    # 🧾 Salvar .txt com a mensagem
    caminho_txt = PASTA_IMAGENS / f"anuncio_{i+1}.txt"
    with open(caminho_txt, "w", encoding="utf-8") as f:
        f.write(mensagem)

    # 🖼️ Baixar imagem
    caminho_img = PASTA_IMAGENS / f"anuncio_{i+1}.jpg"
    try:
        response = requests.get(imagem_url, timeout=10)
        response.raise_for_status()
        with open(caminho_img, "wb") as img_file:
            img_file.write(response.content)
        print(f"✅ Imagem e anúncio gerados: {caminho_txt.name}")
    except Exception as e:
        print(f"❌ Erro ao baixar imagem: {imagem_url} — {e}")
