import requests
import time
import os
import threading
import asyncio
import edge_tts
import re
from config import TELEGRAM_TOKEN, GROQ_API_KEY, CEREBRAS_API_KEY
from groq import Groq
from base_conhecimento import buscar_contexto_pessoal, salvar_aprendizado, gerar_diario_hoje, salvar_historico, carregar_historico_recente

TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
groq_client = Groq(api_key=GROQ_API_KEY)
cerebras_client = Groq(api_key=CEREBRAS_API_KEY, base_url="https://api.cerebras.ai/v1")
sessoes = {}

SISTEMA_PROMPT = """You are Guy, a funny casual American guy teaching English and tech to your Brazilian friend Ariana.
Ariana is studying IT (4th semester), learning English from scratch, UX/UI, web development and other IT areas.
Your style:
- You're a friend, not a teacher — you're learning together
- ALWAYS respond in English, regardless of what language Ariana writes in
- Ask ONE question at a time and wait for the answer
- Analyze EXACTLY what she said — if she seems confused, add a Portuguese translation at the end
- If she gets something wrong, correct her gently and with humor
- Celebrate when she gets it right, then go deeper
- Be fun and use light humor
- Keep it concise — max 3 paragraphs
- End with ONE question or challenge
- When using a tech term, give pronunciation and Portuguese translation
- If she says "escreve" → respond in English text only
- If she says "traduz" → respond in English + Portuguese translation
- If she says "repete" → repeat your last message
- If she seems lost or says "não entendi" → explain in Portuguese"""

def detectar_intencao(texto):
    texto_lower = texto.lower()
    if any(x in texto_lower for x in ["youtube.com", "youtu.be"]):
        return "video"
    if any(x in texto_lower for x in ["/processar", "processa", "analisa", "analise"]):
        return "processar"
    if any(x in texto_lower for x in ["flashcard", "flash card", "cartão", "cartao"]):
        return "flashcard"
    if any(x in texto_lower for x in ["relatorio", "relatório", "diario", "diário", "o que aprendi"]):
        return "relatorio"
    if any(x in texto_lower for x in ["gera questao", "gera questão", "cria questao", "cria questão", "questoes sobre", "questões sobre", "me faz", "me dá exercicio", "exercicios sobre", "exercícios sobre"]):
        return "questoes"
    if any(x in texto_lower for x in ["faz resumo", "faz um resumo", "resume isso", "quero resumo", "me resume"]):
        return "resumo"
    if any(x in texto_lower for x in ["/limpar", "recomeça", "recomecar", "reinicia"]):
        return "limpar"
    return "conversa"

def perguntar_groq(mensagens):
    for cliente, nome in [(groq_client, "Groq"), (cerebras_client, "Cerebras")]:
        try:
            resposta = cliente.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=mensagens,
                temperature=0.7,
                max_tokens=1000
            )
            return resposta.choices[0].message.content
        except Exception as e:
            if "rate_limit" in str(e).lower() or "429" in str(e):
                print(f"{nome} limite atingido, tentando proximo...")
                continue
            raise e
    return "Limite atingido em todos os servicos. Tente apos as 21h." 

def transcrever_voz(caminho_audio):
    with open(caminho_audio, "rb") as f:
        transcricao = groq_client.audio.transcriptions.create(
            model="whisper-large-v3",
            file=f,
            language="pt"
        )
    return transcricao.text

async def gerar_audio_async(texto, arquivo, voz="en-US-GuyNeural"):
    communicate = edge_tts.Communicate(texto, voz)
    await communicate.save(arquivo)

def falar_em_partes(chat_id, texto, voz="en-US-GuyNeural"):
    """Voz padrão: amigo americano (en-US-GuyNeural)"""
    sentencas = re.split(r'(?<=[.!?])\s+', texto)
    partes = []
    parte_atual = ""
    for s in sentencas:
        if len(parte_atual) + len(s) < 400:
            parte_atual += " " + s
        else:
            if parte_atual:
                partes.append(parte_atual.strip())
            parte_atual = s
    if parte_atual:
        partes.append(parte_atual.strip())
    for i, parte in enumerate(partes):
        arquivo = f"/tmp/voz_{chat_id}_{i}.mp3"
        asyncio.run(gerar_audio_async(parte, arquivo, voz))
        if not os.path.exists(arquivo):
            continue
        enviar_audio_telegram(chat_id, arquivo)
        os.remove(arquivo)
        time.sleep(0.3)

def falar_diario(chat_id, texto_pt, texto_en):
    """
    Relatório/diário bilíngue:
    - Parte em português: en-US-GuyNeural (amigo narrando)
    - Parte em 1ª pessoa em inglês: en-US-AriaNeural (voz da Ariana)
    """
    # Manda o texto primeiro
    enviar_mensagem(chat_id, f"🇧🇷 {texto_pt}")
    enviar_mensagem(chat_id, f"🇺🇸 {texto_en}")

    # Áudio PT — voz do amigo
    falar_em_partes(chat_id, texto_pt, voz="pt-BR-AntonioNeural")
    # Áudio EN — voz da Ariana (1ª pessoa)
    falar_em_partes(chat_id, texto_en, voz="en-US-AriaNeural")

def enviar_mensagem(chat_id, texto):
    requests.post(f"{TELEGRAM_URL}/sendMessage", json={
        "chat_id": str(chat_id),
        "text": texto
    })

def enviar_audio_telegram(chat_id, caminho):
    with open(caminho, "rb") as f:
        requests.post(f"{TELEGRAM_URL}/sendVoice",
            data={"chat_id": str(chat_id)},
            files={"voice": f}
        )

def baixar_arquivo_telegram(file_id, extensao):
    info = requests.get(f"{TELEGRAM_URL}/getFile",
        params={"file_id": file_id}).json()
    file_path = info["result"]["file_path"]
    url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"
    conteudo = requests.get(url).content
    caminho = f"/tmp/arquivo_{file_id}.{extensao}"
    with open(caminho, "wb") as f:
        f.write(conteudo)
    return caminho

def obter_updates(offset=0):
    response = requests.get(f"{TELEGRAM_URL}/getUpdates", params={
        "offset": offset,
        "timeout": 30
    })
    return response.json()

def get_sessao(chat_id):
    if chat_id not in sessoes:
        sessoes[chat_id] = {
            "estado": "normal",
            "materiais": [],
            "videos": [],
            "semana": None,
            "historico": [{"role": "system", "content": SISTEMA_PROMPT}] + carregar_historico_recente(20)
        }
    return sessoes[chat_id]

def gerar_flashcards(tema, chat_id):
    enviar_mensagem(chat_id, f"Generating flashcards about {tema}...")
    contexto = buscar_contexto_pessoal(tema)
    resposta = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{
            "role": "user",
            "content": f"""Create 10 flashcards about {tema} based on this content:
{contexto}
Format:
FRONT: (question or English term)
BACK: (answer or translation + practical example)
---"""
        }],
        temperature=0.3,
        max_tokens=2000
    )
    enviar_mensagem(chat_id, resposta.choices[0].message.content)

def gerar_questoes(tema, chat_id):
    enviar_mensagem(chat_id, f"Generating questions about {tema}...")
    contexto = buscar_contexto_pessoal(tema)
    resposta = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{
            "role": "user",
            "content": f"""Create 5 exam questions about {tema} based on this content:
{contexto}
Include both essay and multiple choice questions.
After each question include the commented answer key."""
        }],
        temperature=0.3,
        max_tokens=2000
    )
    enviar_mensagem(chat_id, resposta.choices[0].message.content)

def processar_mensagem(chat_id, mensagem):
    from transcrever import processar_youtube
    from notificacoes import verificar_resposta, tem_notificacao_pendente

    sessao = get_sessao(chat_id)
    texto_usuario = ""

    if "voice" in mensagem:
        caminho = baixar_arquivo_telegram(mensagem["voice"]["file_id"], "ogg")
        texto_usuario = transcrever_voz(caminho)
        os.remove(caminho)
        enviar_mensagem(chat_id, f'🎤 Got it: "{texto_usuario}"')

    elif "text" in mensagem:
        texto_usuario = mensagem["text"]

    elif "document" in mensagem:
        doc = mensagem["document"]
        nome = doc.get("file_name", "arquivo")
        ext = nome.split(".")[-1].lower() if "." in nome else "pdf"
        caminho = baixar_arquivo_telegram(doc["file_id"], ext)
        sessao["materiais"].append(caminho)
        enviar_mensagem(chat_id,
            f"✅ {nome} received!\n"
            f"Total: {len(sessao['materiais'])} file(s)\n"
            f"Send more or say 'processar' to start!"
        )
        return

    elif "photo" in mensagem:
        foto = mensagem["photo"][-1]
        caminho = baixar_arquivo_telegram(foto["file_id"], "jpg")
        sessao["materiais"].append(caminho)
        caption = mensagem.get("caption", "")
        if caption:
            sessao["materiais"].append(f"INSTRUCAO: {caption}")
        enviar_mensagem(chat_id,
            f"✅ Photo received!\n"
            f"Total: {len(sessao['materiais'])} file(s)\n"
            f"Send more or say 'processar' to start!"
        )
        return

    if not texto_usuario:
        return

    # Se tem notificação pendente, passa pro módulo de notificações primeiro
    if tem_notificacao_pendente():
        tratado = verificar_resposta(texto_usuario)
        if tratado:
            return

    intencao = detectar_intencao(texto_usuario)

    if intencao == "video":
        links = re.findall(r'https?://\S+', texto_usuario)
        for link in links:
            if "youtube" in link or "youtu.be" in link:
                sessao["videos"].append(link.strip())
        from fila import salvar_fila
        salvar_fila(sessao["videos"], sessao["materiais"])
        if sessao["videos"]:
            sessao["estado"] = "aguardando_materiais"
            enviar_mensagem(chat_id,
                f"✅ {len(sessao['videos'])} video(s) received!\n\n"
                f"Send support materials if you have them:\n"
                f"📄 PDFs, 📸 Photos, 🔗 Links\n\n"
                f"When done say 'processar'!\n"
                f"No material? Say 'processar' now!"
            )
        return

    if intencao == "processar":
        if not sessao["videos"]:
            enviar_mensagem(chat_id, "Send the YouTube link first!")
            return
        total = len(sessao["videos"])
        enviar_mensagem(chat_id,
            f"🚀 Starting analysis of {total} video(s)!\n"
            f"Materials: {len(sessao['materiais'])}\n"
            f"This might take a few minutes..."
        )
        def rodar():
            try:
                with open("/tmp/processando_video.txt", "w") as f:
                    f.write("1")
                from fila import salvar_fila, remover_video_processado
                for i, url in enumerate(sessao["videos"]):
                    enviar_mensagem(chat_id, f"📹 Processando vídeo {i+1}/{total}...")
                    resultado = processar_youtube(url, sessao["materiais"])
                    remover_video_processado(url)
                    sessao["videos"] = [v for v in sessao["videos"] if v != url]
                    salvar_fila(sessao["videos"], sessao["materiais"])
                    if resultado is None:
                        enviar_mensagem(chat_id, f"⚠️ Vídeo {i+1} pulado — sem áudio disponível")
                sessao["estado"] = "normal"
                sessao["videos"] = []
                sessao["materiais"] = []
                enviar_mensagem(chat_id, f"✅ Todos os {total} vídeos foram analisados!")
            except Exception as e:
                enviar_mensagem(chat_id, f"Erro: {e}")
            finally:
                if os.path.exists("/tmp/processando_video.txt"):
                    os.remove("/tmp/processando_video.txt")
        threading.Thread(target=rodar, daemon=True).start()
        return

    if intencao == "relatorio":
        enviar_mensagem(chat_id, "Generating your daily diary... 📖")
        diario_pt, diario_en = gerar_diario_hoje()
        falar_diario(chat_id, diario_pt, diario_en)
        return

    if intencao == "flashcard":
        tema = texto_usuario.lower()
        for palavra in ["flashcard", "flash card", "cartão", "cartao", "me", "faz", "cria", "sobre", "de"]:
            tema = tema.replace(palavra, "").strip()
        if not tema:
            tema = "the last studied subject"
        gerar_flashcards(tema, chat_id)
        return

    if intencao == "questoes":
        tema = texto_usuario.lower()
        for palavra in ["questao", "questão", "prova", "exercicio", "exercício", "cria", "gera", "sobre", "de", "me"]:
            tema = tema.replace(palavra, "").strip()
        if not tema:
            tema = "the last studied subject"
        gerar_questoes(tema, chat_id)
        return

    if intencao == "limpar":
        sessoes[chat_id] = None
        get_sessao(chat_id)
        enviar_mensagem(chat_id, "Fresh start! What are we learning today? 😄")
        return

    contexto_aulas = buscar_contexto_pessoal(texto_usuario)
    if contexto_aulas:
        sessao["historico"].append({
            "role": "system",
            "content": f"Use this content from Ariana's classes to help answer:\n{contexto_aulas[:2000]}"
        })

    sessao["historico"].append({
        "role": "user",
        "content": texto_usuario
    })

    resposta = perguntar_groq(sessao["historico"])

    sessao["historico"].append({
        "role": "assistant",
        "content": resposta
    })

    if len(sessao["historico"]) > 24:
        sistema = sessao["historico"][0]
        sessao["historico"] = [sistema] + sessao["historico"][-20:]

    salvar_aprendizado(texto_usuario, resposta)
    from fila import salvar_ultimo_tema
    tema_detectado = next((t for t in ["HTML", "CSS", "JavaScript", "Python", "Git", "UX Design", "Figma", "banco de dados", "responsive design", "acessibilidade"] if t.lower() in texto_usuario.lower()), "")
    if tema_detectado:
        salvar_ultimo_tema(tema_detectado)
    salvar_historico("user", texto_usuario, tema_detectado)
    salvar_historico("assistant", resposta, tema_detectado)
    # Resposta em áudio — sempre voz do amigo americano
    falar_em_partes(chat_id, resposta, voz="en-US-GuyNeural")
    
def iniciar_bot():
    print("Bot iniciado com Groq!")
    offset = 0
    while True:
        try:
            updates = obter_updates(offset)
            for update in updates.get("result", []):
                offset = update["update_id"] + 1
                if "message" in update:
                    chat_id = str(update["message"]["chat"]["id"])
                    with open("/tmp/ultima_mensagem.txt", "w") as f:
                        f.write(str(time.time()))
                    threading.Thread(
                        target=processar_mensagem,
                        args=(chat_id, update["message"]),
                        daemon=True
                    ).start()
        except Exception as e:
            print(f"Erro: {e}")
            time.sleep(5)

if __name__ == "__main__":
    iniciar_bot()