import json
import os
from datetime import datetime
from groq import Groq
from config import GROQ_API_KEY

groq_client = Groq(api_key=GROQ_API_KEY)
BASE_FILE = "/home/ubuntu/ariana-tutor/base_dados.json"

def carregar_base():
    if os.path.exists(BASE_FILE):
        with open(BASE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"aulas": [], "aprendizado": [], "ultimo_tema": ""}

def salvar_base(base):
    with open(BASE_FILE, "w", encoding="utf-8") as f:
        json.dump(base, f, ensure_ascii=False, indent=2)

def salvar_historico(chat_id, historico, tema=""):
    base = carregar_base()
    base[f"historico_{chat_id}"] = historico[-20:]
    salvar_base(base)

def carregar_historico_recente(chat_id):
    base = carregar_base()
    return base.get(f"historico_{chat_id}", [])

def buscar_contexto_pessoal(pergunta):
    base = carregar_base()
    aulas = base.get("aulas", [])
    if not aulas:
        return ""
    pergunta_lower = pergunta.lower()
    relevantes = [a["conteudo"] for a in aulas if any(
        p in a.get("conteudo", "").lower() for p in pergunta_lower.split()[:5]
    )]
    return "\n\n".join(relevantes[:2])[:2000] if relevantes else ""

def salvar_aprendizado(pergunta, resposta, tema=""):
    base = carregar_base()
    base["aprendizado"].append({
        "data": datetime.now().strftime("%Y-%m-%d"),
        "hora": datetime.now().strftime("%H:%M"),
        "pergunta": pergunta,
        "resposta": resposta[:500],
        "tema": tema
    })
    base["aprendizado"] = base["aprendizado"][-200:]
    if tema:
        base["ultimo_tema"] = tema
    salvar_base(base)

def salvar_aula(titulo, conteudo, materia="geral", semana=None):
    base = carregar_base()
    base["aulas"].append({
        "titulo": titulo,
        "conteudo": conteudo[:5000],
        "materia": materia,
        "data": datetime.now().strftime("%Y-%m-%d")
    })
    salvar_base(base)

def gerar_diario_hoje():
    base = carregar_base()
    hoje = datetime.now().strftime("%Y-%m-%d")
    aprendizados_hoje = [a for a in base.get("aprendizado", []) if a["data"] == hoje]
    if not aprendizados_hoje:
        return "Nenhum registro de hoje ainda."
    conteudo = "\n".join([f"- {a['pergunta']}" for a in aprendizados_hoje])
    resposta = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "Escreva um diário de aprendizado em primeira pessoa como se fosse a Ariana, animada e orgulhosa. Em português. Máximo 5 linhas."},
            {"role": "user", "content": f"Hoje eu perguntei sobre:\n{conteudo}"}
        ],
        temperature=0.7,
        max_tokens=300
    )
    return resposta.choices[0].message.content
