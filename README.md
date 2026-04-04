# 🤖 Ariana Tutor — Sistema de IA para Aprendizado

Sistema pessoal de IA para aprendizado de TI, UX/UI e inglês, construído do zero com Python.

## ✨ Funcionalidades

- 🎓 **Tutor socrático** via Telegram — responde perguntas de forma didática
- 🌎 **Bilíngue** — respostas em inglês e português com áudio de nativo
- 📹 **Transcrição de videoaulas** — analisa YouTube e arquivos locais
- 📚 **Fontes confiáveis** — cruza com MDN, Wikipedia e Nielsen Norman
- 📊 **Relatório diário** — registra seu progresso automaticamente
- ☁️ **Google Drive** — salva análises organizadas por categoria
- 🔔 **Notificações horárias** — curiosidades e desafios no Telegram

## 🛠️ Tecnologias

- Python 3.12
- Whisper (OpenAI) — transcrição de áudio
- Groq API — LLM rápido e gratuito
- Ollama + LLaMA 3.2 — modelo local
- Edge TTS — voz de nativo americano
- Telegram Bot API
- Google Drive API via rclone
- DuckDuckGo Search
- Wikipedia API

## 🚀 Como usar

1. Clone o repositório
2. Instale as dependências
3. Copie o arquivo de configuração: cp config_exemplo.py config.py
4. Preencha suas chaves em config.py
5. Configure o rclone com Google Drive
6. Rode o sistema: python3 iniciar.py

## 📁 Estrutura

- tutor.py — Bot principal do Telegram
- notificacoes.py — Notificações horárias
- transcrever.py — Transcrição de videoaulas
- relatorio.py — Relatório diário
- iniciar.py — Inicia tudo junto
- google_drive.py — Integração com Drive
- config_exemplo.py — Modelo de configuração

## 👩‍💻 Sobre

Projeto desenvolvido por Ariana — estudante de TI no 4º semestre,
construído do zero como ferramenta pessoal de estudo e aprendizado.