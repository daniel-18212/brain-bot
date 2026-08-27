# 🧠 BrainBot v2.0 - Institutional-Grade Telegram AI Assistant

> **Assistente de Inteligência Artificial Institucional para Telegram**, construído com arquitetura modular de alta disponibilidade, roteamento multi-modelos (focado em planos gratuitos), **gerenciamento de pacotes via Astral `uv` (Rust)**, proteção anti-crash com *circuit breakers*, e **Painel de Controle Administrativo completo via Telegram**.

---

## 🏛️ Recursos de Nível Institucional

* 🚀 **Astral `uv` Nativo:** Construção de containers e resolução de dependências em milissegundos.
* 🛡️ **Arquitetura Anti-Crash & Resiliência:**
  * *Circuit Breakers* para auto-recuperação e desvio de tráfego de provedores de IA instáveis.
  * Supervisão global de exceções assíncronas para operação contínua 24/7 sem paradas.
* 🎛️ **Painel de Controle Master via Telegram (`/admin`):**
  * 🖥️ **Telemetria ao Vivo:** Monitoramento de CPU, RAM, Disco, Tamanho do DB e Uptime do processo.
  * 📈 **Métricas de Negócio (SaaS):** Usuários ativos, mensagens diárias, custos e quotas.
  * 👥 **Gerenciador de Usuários:** Promover tiers (`free`, `pro`, `unlimited`), banir e desbanir.
  * 📢 **Sistema de Broadcast:** Envio de comunicados globais em massa com relatório de entrega.
  * 💾 **Backup Sob Demanda:** Comando `/backup` envia o arquivo do banco `.sqlite` direto no Telegram.
  * 🔒 **Alteração de Modo de Acesso em Runtime:** Alterne entre `PUBLIC`, `WHITELIST` e `PRIVATE` sem reiniciar.
* 🔄 **Roteador Inteligente Multi-Modelos:**
  * **Google Gemini 2.0 Flash / 1.5 Pro:** Cota gratuita oficial com contexto massivo e visão.
  * **Groq Cloud (Llama 3.3 70B & DeepSeek R1 Distill):** Velocidade extrema (300+ tok/s) 100% gratuita.
  * **DeepSeek V3 & DeepSeek R1 Oficial:** Modelos de código e raciocínio formal.
  * **OpenRouter Free Router:** Roteamento dinâmico entre modelos open-source gratuitos.
* 👁️ **Visão Multimodal Computacional:** Análise de fotos, diagramas, notas fiscais e OCR.
* 🎙️ **Transcrição de Voz Instantânea:** Áudios do Telegram processados via Groq Whisper.
* 📄 **Leitura e Extração de Documentos:** Suporte a PDFs, TXT, CSV e códigos-fonte.
* 🌐 **Busca na Web em Tempo Real:** DuckDuckGo Search com síntese contextual.
* 🎨 **Geração de Imagens HD:** Renderização com Flux.1.
* 🗄️ **Banco de Dados SQLite Assíncrono (WAL Mode):** Isolamento de sessões e concorrência segura.
* 🐳 **100% Dockerizado:** Pronto para Linux Mint, VPS ou Raspberry Pi.

---

## 📁 Estrutura de Diretórios

```
brain-bot/
├── .env.example            # Template de variáveis e chaves
├── .env                    # Chaves de API locais (ignorado no Git)
├── .gitignore              # Proteção de credenciais e bancos
├── pyproject.toml          # Configuração de projeto e dependências UV (PEP 621)
├── Dockerfile              # Imagem de produção ultrarrápida com Astral UV
├── docker-compose.yml      # Orquestração do serviço e volume persistente
├── Makefile                # Automação completa de ciclo de vida
├── README.md               # Documentação técnica
├── data/                   # Volume persistente do banco SQLite
└── app/
    ├── config.py           # Validador e carregador de configurações
    ├── main.py             # Entrypoint com supervisor anticrash
    ├── database/
    │   └── db.py           # SQLite Assíncrono com WAL, quotas e auditoria
    ├── core/
    │   ├── router.py       # Roteador Multi-Provedores com Fallback
    │   ├── resilience.py   # Circuit Breakers e Telemetria de Sistema
    │   ├── vision.py       # Visão via Gemini Flash (100% grátis)
    │   ├── audio.py        # Transcrição instantânea com Groq Whisper
    │   ├── web_search.py   # Busca ao vivo via DuckDuckGo
    │   ├── documents.py    # Leitor de PDFs e código-fonte
    │   └── image_gen.py    # Geração de imagens HD com Flux.1
    └── handlers/
        ├── admin.py        # Painel de Administração Master
        ├── commands.py     # Comandos de usuário (/start, /modelos, /limpar, /status)
        ├── callbacks.py    # Botões inline interativos
        ├── messages.py     # Streaming de texto em tempo real
        └── media.py        # Processamento de Fotos, Áudios e Documentos
```

---

## 🚀 Como Iniciar e Operar

### 1. Configurar Credenciais
Copie o template e preencha suas chaves no `.env`:
```bash
cd "/home/turion/Área de trabalho/brain-bot"
nano .env
```
Campos essenciais:
* `TELEGRAM_BOT_TOKEN`: Token obtido no `@BotFather`
* `ADMIN_USER_ID`: Seu ID numérico do Telegram (obtido no `@userinfobot`)
* `GEMINI_API_KEY`, `GROQ_API_KEY` (Gratuitas) e `DEEPSEEK_API_KEY`

### 2. Iniciar via Docker (Recomendado para Produção)
```bash
make up
```

### 3. Acompanhar Logs
```bash
make logs
```

### 4. Parar o Serviço
```bash
make down
```

---

## 🎛️ Comandos do Painel Administrativo

| Comando | Descrição |
| :--- | :--- |
| `/admin` | Abre o Dashboard Interativo com telemetria, métricas e controles |
| `/broadcast <texto>` | Envia mensagem em massa para todos os usuários cadastrados |
| `/promover <ID> <free\|pro\|unlimited>` | Altera o plano de acesso do usuário |
| `/ban <ID>` | Bloqueia o acesso de um usuário ao servidor |
| `/unban <ID>` | Desbloqueia um usuário |
