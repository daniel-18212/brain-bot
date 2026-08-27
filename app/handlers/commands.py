"""
Telegram Bot Command Handlers (Top 4 Elite AI Engines).
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode, ChatAction
from telegram.ext import Application, CommandHandler, ContextTypes
from app.config import settings
from app.database import db
from app.core import llm_router, web_search_engine, image_generator

def is_authorized(user_id: int) -> bool:
    if settings.ACCESS_MODE == "PRIVATE":
        return user_id == settings.ADMIN_USER_ID
    elif settings.ACCESS_MODE == "WHITELIST":
        return user_id in settings.WHITELIST_USERS
    return True

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await update.message.reply_text("⛔ Acesso não autorizado a este servidor.")
        return

    user = await db.get_or_create_user(
        user_id=user_id,
        username=update.effective_user.username or "",
        first_name=update.effective_user.first_name or ""
    )

    welcome_text = (
        f"👋 *Olá, {update.effective_user.first_name}! Bem-vindo ao BrainBot.*\n"
        "Seu assistente institucional de IA conectado aos 4 motores mais avançados do mundo.\n\n"
        "🤖 *Modelo Ativo:* `" + user['selected_model'].upper() + "`\n\n"
        "📌 *Comandos Rápidos:*\n"
        "• ⚙️ `/modelos` - Alternar entre DeepSeek, Gemini, Groq e GPT-4o\n"
        "• 🌐 `/web <busca>` - Pesquisa ao vivo na internet\n"
        "• 🎨 `/imagem <prompt>` - Gerar imagem em alta definição\n"
        "• 🧹 `/limpar` - Reiniciar memória da conversa\n"
        "• 📊 `/status` - Estatísticas de uso e telemetria\n"
        "• 🎭 `/prompt <texto>` - Definir personalidade customizada\n\n"
        "💡 *Recursos Nativos:* Você pode me enviar **Áudios de voz**, **Fotos/OCR**, **PDFs** ou **Códigos** diretamente no chat!"
    )
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN)

async def cmd_modelos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id): return

    keyboard = [
        [
            InlineKeyboardButton("💡 DeepSeek V4/V3 (Código/Texto)", callback_data="set_model:deepseek"),
            InlineKeyboardButton("🔬 DeepSeek R1 (Raciocínio)", callback_data="set_model:deepseek-r1"),
        ],
        [
            InlineKeyboardButton("⚡ Gemini 2.0 Flash (Google Grátis)", callback_data="set_model:gemini"),
            InlineKeyboardButton("🌟 Gemini 1.5 Pro (Google Grátis)", callback_data="set_model:gemini-pro"),
        ],
        [
            InlineKeyboardButton("🚀 Llama 3.3 70B (Groq 300+ tok/s)", callback_data="set_model:groq-llama"),
        ],
        [
            InlineKeyboardButton("🟢 GPT-4o Oficial (GitHub Models)", callback_data="set_model:github-gpt4o"),
            InlineKeyboardButton("🟢 GPT-4o Mini (GitHub Models)", callback_data="set_model:github-gpt4o-mini"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "⚙️ *Selecione o motor de IA que você deseja utilizar:*",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

async def cmd_limpar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id): return
    await db.clear_history(user_id)
    await update.message.reply_text("🧹 *Memória da conversa reiniciada com sucesso!*", parse_mode=ParseMode.MARKDOWN)

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id): return

    user = await db.get_or_create_user(user_id)
    model_info = llm_router.AVAILABLE_MODELS.get(user['selected_model'], {})

    status_text = (
        "📊 *Status do Sistema & Métricas*\n\n"
        f"🤖 *Modelo Ativo:* {model_info.get('name', user['selected_model'])}\n"
        f"🏢 *Provedor:* {model_info.get('provider', 'N/A')}\n"
        f"📝 *Função:* _{model_info.get('description', '')}_\n"
        f"🔑 *Modo de Acesso:* `{settings.ACCESS_MODE}`\n"
        f"⭐ *Seu Plano:* `{user.get('tier', 'free').upper()}`"
    )
    await update.message.reply_text(status_text, parse_mode=ParseMode.MARKDOWN)

async def cmd_web(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id): return

    query = " ".join(context.args)
    if not query:
        await update.message.reply_text("ℹ️ *Uso:* `/web últimas notícias sobre tecnologia`", parse_mode=ParseMode.MARKDOWN)
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    msg_wait = await update.message.reply_text("🔍 *Consultando a internet em tempo real...*", parse_mode=ParseMode.MARKDOWN)

    results = await web_search_engine.search(query)
    await db.record_usage(user_id, "web_search")
    
    prompt = (
        f"Pergunta do usuário: '{query}'\n\n"
        f"Resultados da busca web ao vivo:\n{results}\n\n"
        "Com base nessas informações atualizadas, elabore uma resposta completa e estruturada."
    )
    await msg_wait.delete()

    from app.handlers.messages import stream_chat_response
    await stream_chat_response(update, context, prompt, user_id)

async def cmd_imagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id): return

    prompt = " ".join(context.args)
    if not prompt:
        await update.message.reply_text("ℹ️ *Uso:* `/imagem um dragão mecânico futurista 8k`", parse_mode=ParseMode.MARKDOWN)
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_PHOTO)
    msg_wait = await update.message.reply_text("🎨 *Renderizando imagem com Flux.1...*", parse_mode=ParseMode.MARKDOWN)

    url_img = image_generator.get_image_url(prompt)
    await db.record_usage(user_id, "image_gen")

    try:
        await update.message.reply_photo(
            photo=url_img,
            caption=f"🎨 *Prompt:* _{prompt}_",
            parse_mode=ParseMode.MARKDOWN
        )
        await msg_wait.delete()
    except Exception as e:
        await msg_wait.edit_text(f"❌ Erro na renderização: {e}")

async def cmd_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id): return

    custom_p = " ".join(context.args)
    if not custom_p:
        await db.update_user_system_prompt(user_id, None)
        await update.message.reply_text("🔄 Personalidade redefinida para o padrão.", parse_mode=ParseMode.MARKDOWN)
        return

    await db.update_user_system_prompt(user_id, custom_p)
    await update.message.reply_text(f"🎭 Personalidade atualizada:\n_{custom_p}_", parse_mode=ParseMode.MARKDOWN)

def register_commands(app: Application):
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_start))
    app.add_handler(CommandHandler("ajuda", cmd_start))
    app.add_handler(CommandHandler("modelos", cmd_modelos))
    app.add_handler(CommandHandler("limpar", cmd_limpar))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("web", cmd_web))
    app.add_handler(CommandHandler("imagem", cmd_imagem))
    app.add_handler(CommandHandler("prompt", cmd_prompt))
