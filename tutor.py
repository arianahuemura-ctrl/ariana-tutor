import requests
import time
import asyncio
import edge_tts
import wikipediaapi
from groq import Groq
from ddgs import DDGS
from config import TELEGRAM_TOKEN, GROQ_API_KEY

TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
wiki = wikipediaapi.Wikipedia(language='en', user_agent='ArianaBot/1.0')
groq_client = Groq(api_key=GROQ_API_KEY)

PALAVRAS_TECH = ["html", "css", "javascript", "python", "django", "api", "git", "github", "banco de dados", "sql", "mysql", "backend", "frontend", "codigo", "variavel", "array", "loop", "classe"]
PALAVRAS_UX = ["ux", "ui", "design", "figma", "prototipo", "wireframe", "usabilidade", "interface", "usuario", "acessibilidade", "tipografia", "cor", "layout", "componente"]

historico = {}
aguardando = {}

def detectar_tipo(pergunta):
    pergunta_lower = pergunta.lower()
    for palavra in PALAVRAS_UX:
        if palavra in pergunta_lower:
            return "ux"
    for palavra in PALAVRAS_TECH:
        if palavra in pergunta_lower:
            return "tech"
    return "geral"

def buscar_mdn(pergunta):
    try:
        with DDGS() as ddgs:
            resultados = list(ddgs.text(pergunta + " site:developer.mozilla.org", max_results=2))
            return " ".join([r["body"] for r in resultados])[:500]
    except:
        return ""

def buscar_ux(pergunta):
    try:
        with DDGS() as ddgs:
            resultados = list(ddgs.text(pergunta + " UX design Nielsen Norman nngroup.com", max_results=2))
            return " ".join([r["body"] for r in resultados])[:500]
    except:
        return ""

def buscar_wikipedia(pergunta):
    page = wiki.page(pergunta)
    if page.exists():
        return page.summary[:500]
    return ""

def buscar_contexto(pergunta):
    if len(pergunta) < 15:
        return ""
    tipo = detectar_tipo(pergunta)
    if tipo == "tech":
        return buscar_mdn(pergunta)
    elif tipo == "ux":
        return buscar_ux(pergunta)
    else:
        return buscar_wikipedia(pergunta)

def perguntar_groq(pergunta, historico_conversa=""):
    contexto = buscar_contexto(pergunta)
    resposta = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": f"""You are Ari, a helpful and friendly tutor specializing in technology, UX design and English.
You are talking to Ariana, a Brazilian IT student.
Use reliable sources and be confident in your answers.
Context from search: {contexto}
Previous conversation: {historico_conversa}
Always answer in this exact format:
EN: (answer in English, max 3 lines)
PT: (same answer in Portuguese, max 3 lines)
WORD: (1 key English word) = (pronunciation) = (meaning in Portuguese)
SAY IT: (how to say the user's question in English, natural and casual)"""
            },
            {
                "role": "user",
                "content": pergunta
            }
        ],
        temperature=0.3,
        max_tokens=500
    )
    return resposta.choices[0].message.content

async def gerar_audio(texto, velocidade="en-US-GuyNeural"):
    communicate = edge_tts.Communicate(texto, voice=velocidade)
    await communicate.save("/tmp/resposta.mp3")

def enviar_mensagem(chat_id, texto):
    requests.post(f"{TELEGRAM_URL}/sendMessage", json={
        "chat_id": chat_id,
        "text": texto
    })

def enviar_audio(chat_id, texto, voz="en-US-GuyNeural"):
    if texto:
        asyncio.run(gerar_audio(texto, voz))
        with open("/tmp/resposta.mp3", "rb") as audio:
            requests.post(f"{TELEGRAM_URL}/sendVoice", files={
                "voice": audio
            }, data={"chat_id": chat_id})

def extrair_partes(resposta):
    en, pt, word, say_it = "", "", "", ""
    for linha in resposta.split('\n'):
        if linha.startswith("EN:"):
            en = linha.replace("EN:", "").strip()
        elif linha.startswith("PT:"):
            pt = linha.replace("PT:", "").strip()
        elif linha.startswith("WORD:"):
            word = linha.replace("WORD:", "").strip()
        elif linha.startswith("SAY IT:"):
            say_it = linha.replace("SAY IT:", "").strip()
    return en, pt, word, say_it

def obter_updates(offset=0):
    response = requests.get(f"{TELEGRAM_URL}/getUpdates", params={
        "offset": offset,
        "timeout": 30
    })
    return response.json()

def iniciar_bot():
    print("Bot iniciado com Groq!")
    offset = 0
    while True:
        try:
            updates = obter_updates(offset)
            for update in updates.get("result", []):
                offset = update["update_id"] + 1
                if "message" in update:
                    chat_id = update["message"]["chat"]["id"]
                    texto_original = update["message"].get("text", "").strip()
                    texto = texto_original.lower()
                    if not texto:
                        continue

                    print(f"Mensagem: {texto}")
                    with open("/tmp/ultima_mensagem.txt", "w") as f:
                        f.write(str(time.time()))
                    if ("youtube.com" in texto or "youtu.be" in texto) and texto.startswith("http"):
                        enviar_mensagem(chat_id, "Recebi o link! Processando a aula... pode demorar alguns minutos.")
                        from transcrever import processar_youtube
                        processar_youtube(texto_original)
                        continue

                    if chat_id in aguardando:
                        estado = aguardando[chat_id]

                        if texto == "repete":
                            enviar_audio(chat_id, estado["en"], "en-US-GuyNeural")
                            enviar_mensagem(chat_id, "Ouviu de novo! Me conta o que entendeu. Se quiser o texto escreve 'escreve'.")
                            continue

                        elif texto == "escreve":
                            enviar_mensagem(chat_id, f"EN: {estado['en']}")
                            enviar_mensagem(chat_id, "Entendeu agora? Se quiser a traducao manda 'traduz'.")
                            continue

                        elif texto == "traduz":
                            enviar_mensagem(chat_id, f"PT: {estado['pt']}\nWORD: {estado['word']}\nSAY IT: {estado['say_it']}")
                            del aguardando[chat_id]
                            continue

                        else:
                            enviar_mensagem(chat_id, f"EN: {estado['en']}\nPT: {estado['pt']}\nWORD: {estado['word']}\nSAY IT: {estado['say_it']}")
                            del aguardando[chat_id]
                            from relatorio import registrar_aprendizado
                            registrar_aprendizado(estado["pergunta"], estado["en"])
                            continue

                    contexto_conversa = historico.get(chat_id, "")
                    resposta = perguntar_groq(texto, contexto_conversa)
                    historico[chat_id] = f"Pergunta: {texto} Resposta: {resposta}"
                    from relatorio import registrar_aprendizado
                    registrar_aprendizado(texto, resposta)

                    en, pt, word, say_it = extrair_partes(resposta)
                    aguardando[chat_id] = {
                        "pergunta": texto,
                        "en": en,
                        "pt": pt,
                        "word": word,
                        "say_it": say_it
                    }

                    en_curto = en.split('.')[0] + '.' if en else ""
                    enviar_audio(chat_id, en_curto)
                    enviar_mensagem(chat_id, "👆 O que você entendeu? Me conta!\nComandos: 'repete' | 'escreve' | 'traduz'")

        except Exception as e:
            print(f"Erro: {e}")
            time.sleep(5)

if __name__ == "__main__":
    iniciar_bot()