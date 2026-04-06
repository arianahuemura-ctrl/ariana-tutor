import threading
import subprocess
import time
import os
import json

FILA_FILE = "/home/ubuntu/ariana-tutor/fila_videos.json"

def rodar_tutor():
    while True:
        subprocess.run(["/home/ubuntu/ariana-tutor/venv/bin/python3", "tutor.py"])
        time.sleep(3)

def rodar_notificacoes():
    while True:
        subprocess.run(["/home/ubuntu/ariana-tutor/venv/bin/python3", "notificacoes.py"])
        time.sleep(3)

def retomar_fila_pendente():
    if not os.path.exists(FILA_FILE):
        return
    with open(FILA_FILE) as f:
        dados = json.load(f)
    videos = dados.get("videos", [])
    if not videos:
        return
    print(f"Fila pendente encontrada: {len(videos)} vídeo(s). Retomando...")
    subprocess.run(["/home/ubuntu/ariana-tutor/venv/bin/python3", "-c", f"""
import sys
sys.path.insert(0, '/home/ubuntu/ariana-tutor')
from transcrever import processar_youtube, enviar_progresso
from fila import carregar_fila, remover_video_processado
import os

videos, materiais = carregar_fila()
total = len(videos)
enviar_progresso(f'▶️ Retomando fila: {{total}} vídeo(s) pendente(s)...')
for i, url in enumerate(videos[:]):
    enviar_progresso(f'📹 Processando vídeo {{i+1}}/{{total}}...')
    try:
        processar_youtube(url, materiais)
        remover_video_processado(url)
    except Exception as e:
        remover_video_processado(url)
        enviar_progresso(f'❌ Erro no vídeo {{i+1}}: {{e}} — pulando...')
enviar_progresso('✅ Fila concluída!')
"""])

if __name__ == "__main__":
    print("Iniciando sistema completo...")

    t1 = threading.Thread(target=rodar_tutor)
    t2 = threading.Thread(target=rodar_notificacoes)
    t3 = threading.Thread(target=retomar_fila_pendente)

    t1.start()
    time.sleep(2)
    t2.start()
    time.sleep(1)
    t3.start()

    print("Bot de respostas: ON")
    print("Notificacoes: ON")

    t1.join()
    t2.join()
    t3.join()