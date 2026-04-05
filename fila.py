import json
import os

FILA_FILE = "/home/ubuntu/ariana-tutor/fila_videos.json"

def salvar_fila(videos, materiais):
    with open(FILA_FILE, "w") as f:
        json.dump({"videos": videos, "materiais": materiais}, f)

def carregar_fila():
    if not os.path.exists(FILA_FILE):
        return [], []
    with open(FILA_FILE) as f:
        dados = json.load(f)
    return dados.get("videos", []), dados.get("materiais", [])

def remover_video_processado(url):
    videos, materiais = carregar_fila()
    videos = [v for v in videos if v != url]
    salvar_fila(videos, materiais)

def limpar_fila():
    if os.path.exists(FILA_FILE):
        os.remove(FILA_FILE)

def fila_vazia():
    videos, _ = carregar_fila()
    return len(videos) == 0
ULTIMO_TEMA_FILE = "/tmp/ultimo_tema.txt"

def salvar_ultimo_tema(tema):
    with open(ULTIMO_TEMA_FILE, "w") as f:
        f.write(tema)

def ler_ultimo_tema():
    if not os.path.exists(ULTIMO_TEMA_FILE):
        return None
    with open(ULTIMO_TEMA_FILE) as f:
        return f.read().strip()
