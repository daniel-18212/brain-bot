"""
Telegram Bot Command Handlers — Modern Executive Design System (v2.5).
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

def is_admin(user_id: int) -> bool:
    return user_id == settings.ADMIN_USER_ID

async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menu Principal Executivo."""
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await update.message.reply_text("⛔ Acesso não autorizado a este servidor.")
        return

    user = await db.get_or_create_user(
        user_id=user_id,
        username=update.effective_user.username or "",
        first_name=update.effective_user.first_name or ""
    )

    model_info = llm_router.AVAILABLE_MODELS.get(user['selected_model'], {})
    model_name = model_info.get('name', user['selected_model'].upper())

    # Layout de Botões Executivos
    keyboard = [
        [
            InlineKeyboardButton("⚡ Trocar Modelo de IA", callback_data="menu:modelos"),
            InlineKeyboardButton("🧹 Novo Chat", callback_data="menu:limpar"),
        ],
        [
            InlineKeyboardButton("🌐 Busca na Web", callback_data="menu:web_help"),
            InlineKeyboardButton("🎨 Criar Imagem HD", callback_data="menu:img_help"),
        ],
        [
            InlineKeyboardButton("📊 Telemetria & Status", callback_data="menu:status"),
            InlineKeyboardButton("🎭 Personalizar Persona", callback_data="menu:prompt_help"),
        ],
    ]

    if is_admin(user_id):
        keyboard.append([
            InlineKeyboardButton("🎛️ Master Admin Control", callback_data="admin:main")
        ])

    keyboard.append([
        InlineKeyboardButton("❓ Guia de Recursos", callback_data="menu:ajuda")
    ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    menu_text = (
        "✨ *BrainBot AI Assistant* • `v2.5`\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"🤖 *Motor Ativo:* {model_name}\n"
        f"🟢 *Status:* `Online 24/7` | ⭐ *Plano:* `{user.get('tier', 'free').upper()}`\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Como posso te ajudar hoje? Escolha uma ação rápida abaixo ou simplesmente digite sua dúvida no chat:"
    )

    if update.callback_query:
        await update.callback_query.edit_message_text(menu_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(menu_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cmd_menu(update, context)

async def cmd_modelos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id): return

    keyboard = [
        [
            InlineKeyboardButton("⚡ DeepSeek V4/V3 (Código & Texto)", callback_data="set_model:deepseek"),
        ],
        [
            InlineKeyboardButton("🧠 DeepSeek R1 (Raciocínio Profundo)", callback_data="set_model:deepseek-r1"),
        ],
        [
            InlineKeyboardButton("⚡ Gemini 2.0 Flash (Contexto 1M)", callback_data="set_model:gemini"),
            InlineKeyboardButton("🌟 Gemini 1.5 Pro (Multimodal)", callback_data="set_model:gemini-pro"),
        ],
        [
            InlineKeyboardButton("🚀 Llama 3.3 70B (Groq 300+ tok/s)", callback_data="set_model:groq-llama"),
        ],
        [
            InlineKeyboardButton("🟢 GPT-4o Oficial (GitHub Models)", callback_data="set_model:github-gpt4o"),
        ],
        [
            InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="menu:main")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = (
        "⚙️ *SELEÇÃO DE MOTOR DE INTELIGÊNCIA ARTIFICIAL*\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "Selecione o modelo que você deseja ativar para suas conversas:"
    )
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

async def cmd_limpar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id): return
    await db.clear_history(user_id)
    text = "🧹 *Memória da conversa reiniciada com sucesso!*\nUm novo chat limpo foi iniciado."
    if update.callback_query:
        back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="menu:main")]])
        await update.callback_query.edit_message_text(text, reply_markup=back_kb, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id): return

    user = await db.get_or_create_user(user_id)
    model_info = llm_router.AVAILABLE_MODELS.get(user['selected_model'], {})

    status_text = (
        "📊 *TELEMETRIA & STATUS DA SESSÃO*\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"🤖 *Motor Ativo:* {model_info.get('name', user['selected_model'])}\n"
        f"🏢 *Provedor:* `{model_info.get('provider', 'N/A')}`\n"
        f"📝 *Foco:* _{model_info.get('description', '')}_\n"
        f"🔒 *Acesso:* `{settings.ACCESS_MODE}` | ⭐ *Plano:* `{user.get('tier', 'free').upper()}`\n"
        f"🩺 *Healthcheck:* `http://localhost:8080/health` (Healthy)"
    )
    
    if update.callback_query:
        back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="menu:main")]])
        await update.callback_query.edit_message_text(status_text, reply_markup=back_kb, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(status_text, parse_mode=ParseMode.MARKDOWN)

async def cmd_web(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id): return

    query = " ".join(context.args)
    if not query:
        await update.message.reply_text("ℹ️ *Uso:* `/web últimas notícias sobre tecnologia`", parse_mode=ParseMode.MARKDOWN)
        return

    from app.handlers.messages import stream_chat_response
    await stream_chat_response(update, context, query, user_id)

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
    app.add_handler(CommandHandler("menu", cmd_menu))
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_menu))
    app.add_handler(CommandHandler("ajuda", cmd_menu))
    app.add_handler(CommandHandler("modelos", cmd_modelos))
    app.add_handler(CommandHandler("limpar", cmd_limpar))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("web", cmd_web))
    app.add_handler(CommandHandler("imagem", cmd_imagem))
    app.add_handler(CommandHandler("prompt", cmd_prompt))
