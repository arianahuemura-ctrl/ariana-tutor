import requests
import asyncio
import edge_tts
import json
import os
from datetime import datetime
from groq import Groq
from config import TELEGRAM_TOKEN, GROQ_API_KEY

TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
CHAT_ID = "6968289835"
groq_client = Groq(api_key=GROQ_API_KEY)
HISTORICO_FILE = "historico_aprendizado.json"

def carregar_historico():
    if os.path.exists(HISTORICO_FILE):
        with open(HISTORICO_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def salvar_historico(historico):
    with open(HISTORICO_FILE, "w", encoding="utf-8") as f:
        json.dump(historico, f, ensure_ascii=False, indent=2)

def registrar_aprendizado(pergunta, resposta):
    historico = carregar_historico()
    hoje = datetime.now().strftime("%Y-%m-%d")
    if hoje not in historico:
        historico[hoje] = []
    historico[hoje].append({
        "hora": datetime.now().strftime("%H:%M"),
        "pergunta": pergunta,
        "resposta": resposta
    })
    salvar_historico(historico)

def gerar_relatorio_diario():
    historico = carregar_historico()
    hoje = datetime.now().strftime("%Y-%m-%d")
    
    if hoje not in historico or not historico[hoje]:
        return None, None
    
    dias_anteriores = {k: v for k, v in historico.items() if k != hoje}
    
    resumo_hoje = "\n".join([f"- Perguntou: {item['pergunta']}" for item in historico[hoje]])
    resumo_anterior = ""
    for data, items in list(dias_anteriores.items())[-3:]:
        for item in items:
            resumo_anterior += f"- {data}: {item['pergunta']}\n"
    
    prompt = f"""You are Ari, an enthusiastic and encouraging tutor talking to Ariana, a Brazilian IT student.
Write a daily learning diary entry AS IF Ariana herself is writing it.
Use first person "I" in English and "Eu" in Portuguese.
She is excited, positive and proud of herself.
Today she learned about:
{resumo_hoje}

Previous days she learned about:
{resumo_anterior}

Write in this format:
EN: (Ariana writing in first person in English, excited and proud, 4-5 lines, mention connections with previous days if any)
PT: (same in Portuguese, first person, 4-5 lines)

Example start: "EN: Today I discovered..." or "EN: Wow, today I finally understood..."
Be enthusiastic and celebrate your own progress!"""
    
    resposta = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=600
    )
    
    conteudo = resposta.choices[0].message.content
    texto_en = ""
    for linha in conteudo.split('\n'):
        if linha.startswith("EN:"):
            texto_en = linha.replace("EN:", "").strip()
            break
    
    return conteudo, texto_en

async def gerar_audio(texto):
    communicate = edge_tts.Communicate(texto, voice="pt-BR-AntonioNeural")
    await communicate.save("/tmp/relatorio.mp3")

def enviar_relatorio():
    conteudo, texto_en = gerar_relatorio_diario()
    if not conteudo:
        return
    
    requests.post(f"{TELEGRAM_URL}/sendMessage", json={
        "chat_id": CHAT_ID,
        "text": f"📚 Daily Report / Relatório do Dia\n\n{conteudo}"
    })
    
    if texto_en:
        asyncio.run(gerar_audio(texto_en))
        with open("/tmp/relatorio.mp3", "rb") as audio:
            requests.post(f"{TELEGRAM_URL}/sendVoice", files={
                "voice": audio
            }, data={"chat_id": CHAT_ID})

if __name__ == "__main__":
    enviar_relatorio()