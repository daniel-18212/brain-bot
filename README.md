# 🧠 BrainBot - Enterprise Multi-Model AI Assistant

> **Assistente de Inteligência Artificial de Alto Nível para Telegram**, projetado com arquitetura modular, maximização de planos gratuitos, suporte multimodal completo e pronto para deploy comercial (SaaS) ou pessoal.

---

## 🚀 Principais Funcionalidades

* ⚡ **Streaming em Tempo Real:** Visualização da resposta sendo digitada ao vivo no Telegram.
* 🔄 **Roteador Inteligente de Modelos (Model Router):**
  * **Google Gemini 2.0 Flash / 1.5 Pro:** Cota gratuita oficial com contexto massivo e visão computacional.
  * **Groq Cloud (Llama 3.3 70B & DeepSeek R1 Distill):** Velocidade extrema gratuita (300+ tokens/s).
  * **DeepSeek V3 & DeepSeek R1 Oficial:** Raciocínio matemático e código de ponta.
  * **OpenRouter Free Router:** Roteamento entre dezenas de modelos abertos gratuitos.
* 👁️ **Visão Computacional Multimodal:** Análise de fotos, diagramas, notas fiscais e OCR.
* 🎙️ **Transcrição Instantânea de Voz:** Áudios do Telegram processados via Groq Whisper em milissegundos.
* 📄 **Leitura e Extração de Documentos:** Análise de PDFs, TXT, CSV e arquivos de código.
* 🌐 **Busca na Web ao Vivo:** Pesquisas em tempo real integradas via DuckDuckGo com síntese automática.
* 🎨 **Geração de Imagens HD:** Renderização de alta fidelidade com Flux.1.
* 🗄️ **Persistência SQLite Assíncrona (WAL Mode):** Histórico de conversas, métricas e isolamento por usuário.
* 🐳 **100% Dockerizado:** Pronto para rodar no Linux Mint, VPS ou Raspberry Pi com 1 comando.

---

## 📁 Estrutura do Projeto

```
brain-bot/
├── .env.example            # Template de variáveis de ambiente
├── .gitignore              # Proteção de chaves e dados
├── Dockerfile              # Imagem multi-stage de produção
├── docker-compose.yml      # Orquestração do container
├── Makefile                # Automação de comandos
├── requirements.txt        # Dependências Python
├── data/                   # Volume persistente do banco SQLite
└── app/
    ├── config.py           # Validação e carregamento de configurações
    ├── database/           # Camada de banco de dados SQLite assíncrono
    ├── core/               # Motores de IA (Router, Visão, Áudio, Busca, Docs, Imagem)
    ├── handlers/           # Comandos, Mensagens, Callbacks e Mídias
    └── main.py             # Entrypoint da aplicação
```

---

## 🔑 Como Obter as Chaves de API (Gratuitas)

1. **Telegram Bot Token:** Abra o [@BotFather](https://t.me/BotFather) no Telegram, envie `/newbot` e copie o token gerado.
2. **Google Gemini (100% Grátis):** Acesse [Google AI Studio](https://aistudio.google.com/), clique em **Get API key**.
3. **Groq Cloud (100% Grátis):** Acesse [Groq Console](https://console.groq.com/), crie sua conta e gere uma chave em **API Keys**.
4. **DeepSeek (Baixo custo):** Acesse [DeepSeek Platform](https://platform.deepseek.com/) e gere sua chave.

---

## ⚙️ Instalação e Execução

### Opção 1: Executando com Docker (Recomendado)

1. Configure seu arquivo `.env`:
   ```bash
   cp .env.example .env
   nano .env  # Preencha suas chaves
   ```

2. Inicie o bot em segundo plano:
   ```bash
   make up
   ```

3. Verifique os logs em tempo real:
   ```bash
   make logs
   ```

4. Para parar o bot:
   ```bash
   make down
   ```

---

### Opção 2: Executando Localmente com Python

1. Crie o ambiente virtual e instale as dependências:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. Execute o bot:
   ```bash
   python3 -m app.main
   ```

---

## 🌐 Publicando no GitHub

```bash
git init
git add .
git commit -m "feat: initial commit - enterprise brain-bot architecture"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/brain-bot.git
git push -u origin main
```

---

## 🔒 Segurança e Controle de Acesso

No arquivo `.env`, você pode definir `ACCESS_MODE`:
* `PRIVATE`: Responde exclusivamente ao `ADMIN_USER_ID`.
* `WHITELIST`: Responde aos IDs definidos em `WHITELIST_USERS`.
* `PUBLIC`: Pronto para operar como SaaS multi-usuário.
