from fastapi import FastAPI, Query
import subprocess
from pathlib import Path
import os

app = FastAPI()

BASE_DIR = Path(__file__).parent

@app.post("/coletar-ofertas")
def coletar_ofertas(qtd: int = Query(100, ge=20, le=2000)):
    """Executa a coleta de ofertas"""
    result = subprocess.run(
        ["python3", str(BASE_DIR / "coletar_ofertas.py"), "--auto", str(qtd)],
        capture_output=True, text=True
    )
    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode
    }

@app.post("/gerar-imagem")
def gerar_imagem():
    """Gera os anúncios em texto/imagem"""
    result = subprocess.run(
        ["python3", str(BASE_DIR / "gerar_imagem.py")],
        capture_output=True, text=True
    )
    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode
    }

@app.post("/enviar-whatsapp")
def enviar_whatsapp():
    """Envia os anúncios via WhatsApp"""

    env = os.environ.copy()
    env["DISPLAY"] = ":0.0" 

    result = subprocess.run(
        ["python3", str(BASE_DIR / "whatsapp.py")],
        capture_output=True, text=True, env=env
    )
    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode
    }