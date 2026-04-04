import requests
import time
import random
import asyncio
import edge_tts
import os
from datetime import datetime
from groq import Groq
from config import TELEGRAM_TOKEN, GROQ_API_KEY

groq_client = Groq(api_key=GROQ_API_KEY)

TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
CHAT_ID = "6968289835"

temas = [
    "Figma", "UX Research", "HTML", "CSS", "JavaScript",
    "Python", "Git", "GitHub", "SQL",
    "design thinking", "prototipagem", "acessibilidade web",
    "tipografia", "paleta de cores", "portfolio de UX",
    "wireframe", "user persona", "jornada do usuario"
]

def gerar_notificacao():
    tema = random.choice(temas)
    resposta = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": """You are a funny casual American guy texting a Brazilian friend named Ariana who is learning UX design and web development.
Send ONE short funny question in English about the topic.
Then translate it naturally to Portuguese.
Format exactly:
EN: (your question in English, max 1 line)
PT: (same in Portuguese, max 1 line)
WORD: (1 main word) = (pronunciation) = (meaning in Portuguese)"""
            },
            {
                "role": "user",
                "content": f"Send a message about: {tema}"
            }
        ],
        temperature=0.8,
        max_tokens=150
    )
    return resposta.choices[0].message.content

async def gerar_audio(texto):
    communicate = edge_tts.Communicate(texto, voice="en-US-GuyNeural")
    await communicate.save("/tmp/notificacao.mp3")

def enviar_notificacao():
    mensagem = gerar_notificacao()
    texto_en = ""
    for linha in mensagem.split('\n'):
        if linha.startswith("EN:"):
            texto_en = linha.replace("EN:", "").strip()
            break

    requests.post(f"{TELEGRAM_URL}/sendMessage", json={
        "chat_id": CHAT_ID,
        "text": mensagem
    })

    if texto_en:
        asyncio.run(gerar_audio(texto_en))
        with open("/tmp/notificacao.mp3", "rb") as audio:
            requests.post(f"{TELEGRAM_URL}/sendVoice", files={
                "voice": audio
            }, data={"chat_id": CHAT_ID})

    print(f"Notificacao enviada!")

ULTIMA_MENSAGEM_FILE = "/tmp/ultima_mensagem.txt"

def registrar_atividade():
    with open(ULTIMA_MENSAGEM_FILE, "w") as f:
        f.write(str(time.time()))

def usuario_ativo():
    if not os.path.exists(ULTIMA_MENSAGEM_FILE):
        return False
    with open(ULTIMA_MENSAGEM_FILE) as f:
        ultima = float(f.read())
    return (time.time() - ultima) < 1800

if __name__ == "__main__":
    import os
    print("Iniciando notificacoes a cada hora...")
    while True:
        hora = datetime.now().hour
        if 7 <= hora < 23 and not usuario_ativo():
            enviar_notificacao()
        elif usuario_ativo():
            print("Usuario ativo, aguardando...")
        else:
            print("Fora do horario, aguardando...")
        time.sleep(3600)