import requests
import time
import random
import asyncio
import edge_tts
import os
from datetime import datetime
from groq import Groq
from config import TELEGRAM_TOKEN, GROQ_API_KEY

TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
CHAT_ID = "6968289835"
groq_client = Groq(api_key=GROQ_API_KEY)

ULTIMA_MENSAGEM_FILE = "/tmp/ultima_mensagem.txt"
PROCESSANDO_FILE = "/tmp/processando_video.txt"

temas = [
    "HTML", "CSS", "JavaScript", "Python", "Git", "GitHub",
    "UX Design", "Figma", "wireframe", "user persona",
    "REST API", "banco de dados SQL", "responsive design",
    "design thinking", "acessibilidade web", "tipografia",
    "color theory", "user testing", "prototipagem", "portfolio"
]

aguardando_resposta = {}

def usuario_ativo():
    if not os.path.exists(ULTIMA_MENSAGEM_FILE):
        return False
    with open(ULTIMA_MENSAGEM_FILE) as f:
        ultima = float(f.read())
    return (time.time() - ultima) < 7200

def processando_video():
    return os.path.exists(PROCESSANDO_FILE)

def gerar_notificacao():
    from fila import ler_ultimo_tema
    ultimo = ler_ultimo_tema()
    tema = ultimo if ultimo else random.choice(temas)
    resposta = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": """You are a casual funny American guy sending a SHORT voice message to your Brazilian friend Ariana.
Ask ONE genuine curious question in English about the topic.
Do NOT assume she knows anything about it.
Be natural, casual, like a real voice message between friends.
Maximum 1 sentence. No translation. No explanation."""
            },
            {
                "role": "user",
                "content": f"Send a casual voice message question about: {tema}"
            }
        ],
        temperature=0.9,
        max_tokens=60
    )
    texto = resposta.choices[0].message.content.strip().replace('"', '')
    return texto, tema

async def gerar_audio(texto, voz="en-US-GuyNeural"):
    communicate = edge_tts.Communicate(texto, voz)
    await communicate.save("/tmp/notificacao.mp3")

def enviar_audio_telegram(texto_en):
    asyncio.run(gerar_audio(texto_en, "en-US-GuyNeural"))
    with open("/tmp/notificacao.mp3", "rb") as audio:
        requests.post(f"{TELEGRAM_URL}/sendVoice", files={
            "voice": audio
        }, data={"chat_id": CHAT_ID})

def enviar_mensagem(texto):
    requests.post(f"{TELEGRAM_URL}/sendMessage", json={
        "chat_id": CHAT_ID,
        "text": texto
    })

def processar_resposta_usuario(texto_usuario):
    if CHAT_ID not in aguardando_resposta:
        return False

    estado = aguardando_resposta[CHAT_ID]
    texto_en = estado["texto_en"]
    tema = estado["tema"]
    texto_lower = texto_usuario.lower().strip()

    if texto_lower == "repete":
        enviar_audio_telegram(texto_en)
        enviar_mensagem("🔁 Ouviu de novo! O que entendeu? Se quiser ver escrito diz 'escreve'.")
        return True

    if texto_lower == "escreve":
        enviar_mensagem(f"📝 {texto_en}\n\nEntendeu agora? Se quiser a tradução diz 'traduz'.")
        return True

    if texto_lower == "traduz":
        traducao = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user",
                "content": f"Traduza para português brasileiro de forma natural e explique o que quis dizer: {texto_en}"}],
            max_tokens=150
        )
        pt = traducao.choices[0].message.content
        enviar_mensagem(f"🇧🇷 O que eu quis dizer foi:\n{pt}")
        del aguardando_resposta[CHAT_ID]
        return True

    if texto_lower in ["não sei", "nao sei", "?", "nao entendi", "não entendi"]:
        ensinar(texto_en, tema)
        del aguardando_resposta[CHAT_ID]
        return True

    # Analisa se entendeu
    analise = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": """You are Ari, an English tutor. Analyze if the student understood the audio.
Be encouraging and correct with kindness.
Respond in Brazilian Portuguese.
Maximum 2 sentences + 1 encouraging question."""
            },
            {
                "role": "user",
                "content": f"The audio said: '{texto_en}'\nThe student responded: '{texto_usuario}'\nDid they understand correctly? Give feedback."
            }
        ],
        temperature=0.5,
        max_tokens=150
    )
    feedback = analise.choices[0].message.content
    enviar_mensagem(feedback)
    del aguardando_resposta[CHAT_ID]
    return True

def ensinar(texto_en, tema):
    """Ensina o tema passo a passo quando o usuário não sabe"""
    resposta = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": """Você é a Ari, tutora da Ariana.
Ela não conhece nada sobre o tema ainda.
Ensine o primeiro conceito básico de forma simples e divertida.
Máximo 3 linhas.
Termine perguntando se entendeu antes de continuar."""
            },
            {
                "role": "user",
                "content": f"Ensine o básico sobre '{tema}' para alguém que não sabe nada. Comece do zero."
            }
        ],
        temperature=0.7,
        max_tokens=200
    )
    enviar_mensagem(resposta.choices[0].message.content)

def enviar_notificacao():
    if processando_video():
        print("Processando vídeo, notificação adiada...")
        return

    if usuario_ativo():
        print("Usuário ativo, notificação adiada...")
        return

    texto_en, tema = gerar_notificacao()

    enviar_audio_telegram(texto_en)
    enviar_mensagem("👆 O que você entendeu?\n'repete' | 'escreve' | 'traduz' | 'não sei'")

    aguardando_resposta[CHAT_ID] = {
        "texto_en": texto_en,
        "tema": tema,
        "timestamp": time.time()
    }

    print(f"Notificação enviada: {texto_en}")

if __name__ == "__main__":
    print("Iniciando notificações a cada 2 horas...")
    while True:
        hora = datetime.now().hour
        if 7 <= hora < 23:
            enviar_notificacao()
        else:
            print("Fora do horário, aguardando...")
        time.sleep(7200)