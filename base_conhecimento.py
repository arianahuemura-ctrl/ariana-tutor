import chromadb
import json
import os
from datetime import datetime
from groq import Groq
from config import GROQ_API_KEY

groq_client = Groq(api_key=GROQ_API_KEY)
chroma_client = chromadb.PersistentClient(path="/home/ariana/sistema-tutor/base_dados")

def get_colecao(nome):
    return chroma_client.get_or_create_collection(name=nome)

def salvar_aula(titulo, conteudo, materia="geral", semana=None):
    colecao = get_colecao("aulas")
    doc_id = f"aula_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    metadados = {
        "titulo": titulo,
        "materia": materia,
        "data": datetime.now().strftime("%Y-%m-%d"),
        "semana": str(semana) if semana else "0"
    }
    colecao.add(
        documents=[conteudo],
        metadatas=[metadados],
        ids=[doc_id]
    )
    print(f"Aula salva na base: {titulo}")
    return doc_id

def buscar_aulas(pergunta, n_resultados=3):
    colecao = get_colecao("aulas")
    try:
        resultados = colecao.query(
            query_texts=[pergunta],
            n_results=min(n_resultados, colecao.count())
        )
        if resultados and resultados["documents"][0]:
            return resultados["documents"][0]
    except:
        pass
    return []

def salvar_aprendizado(pergunta, resposta, acertou=None, tema=""):
    colecao = get_colecao("aprendizado")
    doc_id = f"aprend_{datetime.now().strftime('%Y%m%d_%H%M%S%f')}"
    metadados = {
        "data": datetime.now().strftime("%Y-%m-%d"),
        "hora": datetime.now().strftime("%H:%M"),
        "tema": tema,
        "acertou": str(acertou) if acertou is not None else "null"
    }
    colecao.add(
        documents=[f"Pergunta: {pergunta}\nResposta: {resposta}"],
        metadatas=[metadados],
        ids=[doc_id]
    )

def buscar_contexto_pessoal(pergunta):
    aulas = buscar_aulas(pergunta)
    contexto = ""
    if aulas:
        contexto = "CONTEÚDO DAS SUAS AULAS:\n" + "\n\n".join(aulas[:2])[:3000]
    return contexto

def gerar_diario_hoje():
    """
    Retorna uma tupla (diario_pt, diario_en):
    - diario_pt: narrado em 1ª pessoa em português (para referência/texto)
    - diario_en: narrado em 1ª pessoa em inglês (áudio com voz feminina en-US-AriaNeural)
    """
    colecao = get_colecao("aprendizado")
    hoje = datetime.now().strftime("%Y-%m-%d")
    try:
        resultados = colecao.get(where={"data": hoje})
        if not resultados["documents"]:
            msg = "Nothing logged yet today. Start learning and come back later! 😄"
            return msg, msg

        conteudo = "\n".join(resultados["documents"])

        # Versão em português — 1ª pessoa, animada
        resp_pt = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": """Escreva um diário de aprendizado em PRIMEIRA PESSOA como se fosse a Ariana falando.
Tom: animado, divertido, orgulhoso das conquistas do dia.
Mencione o que aprendeu, o que acertou, o que errou e precisa revisar.
Máximo 200 palavras. Em português brasileiro."""
                },
                {
                    "role": "user",
                    "content": f"Histórico de hoje:\n{conteudo[:4000]}"
                }
            ],
            temperature=0.7,
            max_tokens=400
        )
        diario_pt = resp_pt.choices[0].message.content

        # Versão em inglês — 1ª pessoa, mesma vibe
        resp_en = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": """Write a learning diary in FIRST PERSON as if Ariana is speaking.
Tone: excited, fun, proud of the day's wins.
Mention what she learned, got right, got wrong and needs to review.
Maximum 200 words. In casual American English — not too formal."""
                },
                {
                    "role": "user",
                    "content": f"Today's learning log:\n{conteudo[:4000]}"
                }
            ],
            temperature=0.7,
            max_tokens=400
        )
        diario_en = resp_en.choices[0].message.content

        return diario_pt, diario_en

    except Exception as e:
        msg = f"Error generating diary: {e}"
        return msg, msg

if __name__ == "__main__":
    print("Base de conhecimento iniciada!")
    print(f"Aulas salvas: {get_colecao('aulas').count()}")
    print(f"Aprendizados salvos: {get_colecao('aprendizado').count()}")
def salvar_historico(role, conteudo, tema=""):
    colecao = get_colecao("historico")
    doc_id = f"hist_{datetime.now().strftime('%Y%m%d_%H%M%S%f')}"
    colecao.add(
        documents=[conteudo],
        metadatas=[{
            "role": role,
            "data": datetime.now().strftime("%Y-%m-%d"),
            "hora": datetime.now().strftime("%H:%M"),
            "tema": tema
        }],
        ids=[doc_id]
    )

def carregar_historico_recente(n=20):
    colecao = get_colecao("historico")
    total = colecao.count()
    if total == 0:
        return []
    resultados = colecao.get(
        limit=min(n, total),
        include=["documents", "metadatas"]
    )
    pares = list(zip(resultados["metadatas"], resultados["documents"]))
    pares_ordenados = sorted(pares, key=lambda x: x[0].get("hora", ""))
    return [{"role": m["role"], "content": d} for m, d in pares_ordenados]
