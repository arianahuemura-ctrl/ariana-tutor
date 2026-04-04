import whisper
import yt_dlp
import fitz
import asyncio
import edge_tts
import requests
import os
import subprocess
from datetime import datetime
from pptx import Presentation
from groq import Groq
from ddgs import DDGS
from config import TELEGRAM_TOKEN, GROQ_API_KEY

TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
CHAT_ID = "6968289835"
groq_client = Groq(api_key=GROQ_API_KEY)

def baixar_audio_youtube(url):
    print("Baixando audio do YouTube...")
    opts = {
        'format': 'bestaudio/best',
        'outtmpl': '/tmp/aula.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
        }],
        'quiet': True
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])
    return '/tmp/aula.mp3'

def transcrever_audio(caminho_audio):
    print("Transcrevendo audio com Whisper...")
    model = whisper.load_model("base")
    resultado = model.transcribe(caminho_audio)
    return resultado["text"]

def extrair_texto_pdf(caminho_pdf):
    print("Lendo PDF...")
    doc = fitz.open(caminho_pdf)
    texto = ""
    for pagina in doc:
        texto += pagina.get_text()
    return texto[:3000]

def extrair_texto_pptx(caminho_pptx):
    print("Lendo slides...")
    prs = Presentation(caminho_pptx)
    texto = ""
    for slide in prs.slides:
        for shape in slide.shapes:
            if hasattr(shape, "text"):
                texto += shape.text + "\n"
    return texto[:3000]

def buscar_fontes(tema):
    print("Buscando fontes confiaveis...")
    try:
        with DDGS() as ddgs:
            resultados = list(ddgs.text(tema + " MDN developer mozilla OR wikipedia OR nngroup.com", max_results=3))
            return " ".join([r["body"] for r in resultados])[:1000]
    except:
        return ""

def analisar_com_groq(transcricao, material_apoio="", fontes=""):
    print("Analisando com Groq...")
    resposta = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": """You are an expert tutor helping a Brazilian IT student.
Analyze the class transcription in FULL detail - do not summarize, explain everything completely.
Cross-reference with support materials and reliable English sources.
Identify errors or oversimplifications.
Always respond in Brazilian Portuguese."""
            },
            {
                "role": "user",
                "content": f"""Transcrição da aula:
{transcricao}

Material de apoio (slides/PDF):
{material_apoio}

Fontes confiáveis em inglês:
{fontes}

Por favor faça uma análise COMPLETA e DETALHADA:
1. Corrija erros na transcrição explicando o correto
2. Explique TODOS os conceitos mencionados de forma clara e completa
3. Para cada conceito, adicione o que as fontes confiáveis em inglês dizem
4. Indique onde o professor simplificou ou errou e explique o correto
5. Adicione exemplos práticos para cada conceito
6. Faça um resumo final detalhado em tópicos
Não resuma - seja o mais completo e detalhado possível."""
            }
        ],
        temperature=0.2,
        max_tokens=4000
    )
    return resposta.choices[0].message.content

def enviar_resultado(resultado, tema):
    partes = [resultado[i:i+4000] for i in range(0, len(resultado), 4000)]
    for i, parte in enumerate(partes):
        requests.post(f"{TELEGRAM_URL}/sendMessage", json={
            "chat_id": CHAT_ID,
            "text": f"Analise da Aula ({i+1}/{len(partes)}):\n\n{parte}"
        })

    data = datetime.now().strftime("%Y-%m-%d_%H-%M")
    nome_arquivo = f"/tmp/aula_{data}.md"
    with open(nome_arquivo, 'w', encoding='utf-8') as f:
        f.write(f"Analise da Aula - {data}\n")
        f.write("="*50 + "\n\n")
        f.write(resultado)

    subprocess.run([
        'rclone', 'copy', nome_arquivo,
        'gdrive:Ariana Tutor/Videoaulas'
    ])
    print("Salvo no Google Drive em Ariana Tutor/Videoaulas!")

def processar_youtube(url, caminho_material=None):
    audio = baixar_audio_youtube(url)
    transcricao = transcrever_audio(audio)
    material = ""
    if caminho_material:
        if caminho_material.endswith('.pdf'):
            material = extrair_texto_pdf(caminho_material)
        elif caminho_material.endswith('.pptx'):
            material = extrair_texto_pptx(caminho_material)
    fontes = buscar_fontes(transcricao[:200])
    resultado = analisar_com_groq(transcricao, material, fontes)
    enviar_resultado(resultado, "Aula")
    print("Concluido! Resultado enviado no Telegram e salvo no Drive.")
    return resultado

def processar_arquivo(caminho_video, caminho_material=None):
    transcricao = transcrever_audio(caminho_video)
    material = ""
    if caminho_material:
        if caminho_material.endswith('.pdf'):
            material = extrair_texto_pdf(caminho_material)
        elif caminho_material.endswith('.pptx'):
            material = extrair_texto_pptx(caminho_material)
    fontes = buscar_fontes(transcricao[:200])
    resultado = analisar_com_groq(transcricao, material, fontes)
    enviar_resultado(resultado, "Aula")
    print("Concluido! Resultado enviado no Telegram e salvo no Drive.")
    return resultado

if __name__ == "__main__":
    print("Sistema de transcricao pronto!")
    print("Use processar_youtube(url) ou processar_arquivo(caminho)")