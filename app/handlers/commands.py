"""
Telegram Bot Command Handlers — Full Enterprise Feature Suite (v3.0).
"""
import asyncio
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode, ChatAction
from telegram.ext import Application, CommandHandler, ContextTypes
from app.config import settings
from app.database import db
from app.core import (
    llm_router,
    web_search_engine,
    image_generator,
    conversation_exporter,
    SPECIALIZED_ASSISTANTS
)

logger = logging.getLogger(__name__)

def is_authorized(user_id: int) -> bool:
    if settings.ACCESS_MODE == "PRIVATE":
        return user_id == settings.ADMIN_USER_ID
    elif settings.ACCESS_MODE == "WHITELIST":
        return user_id in settings.WHITELIST_USERS
    return True

def is_admin(user_id: int) -> bool:
    return user_id == settings.ADMIN_USER_ID

async def safe_reply(update: Update, text: str, reply_markup=None, parse_mode=ParseMode.MARKDOWN):
    """Envia ou edita mensagem com tentativas automáticas e fallback de formatação."""
    for attempt in range(3):
        try:
            if update.callback_query:
                return await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
            else:
                return await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
        except Exception as e:
            logger.warning(f"Tentativa {attempt+1} de envio falhou: {e}")
            if attempt == 2:
                try:
                    if update.callback_query:
                        return await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
                    else:
                        return await update.message.reply_text(text, reply_markup=reply_markup)
                except Exception as final_e:
                    logger.error(f"Erro fatal ao enviar mensagem: {final_e}")
            await asyncio.sleep(0.5 * (attempt + 1))

async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menu Principal Executivo do BrainBot."""
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await safe_reply(update, "⛔ Acesso não autorizado a este servidor.")
        return

    user = await db.get_or_create_user(
        user_id=user_id,
        username=update.effective_user.username or "",
        first_name=update.effective_user.first_name or ""
    )

    model_info = llm_router.AVAILABLE_MODELS.get(user['selected_model'], {})
    model_name = model_info.get('name', user['selected_model'].upper())
    voice_status = "🔊 Ativo" if user.get("voice_mode_enabled") else "🔇 Desativado"

    keyboard = [
        [
            InlineKeyboardButton("⚡ Motores de IA", callback_data="menu:modelos"),
            InlineKeyboardButton("🎭 Especialistas GPTs", callback_data="menu:assistentes"),
        ],
        [
            InlineKeyboardButton("🎙️ Modo Voz (TTS)", callback_data="menu:toggle_voice"),
            InlineKeyboardButton("🧠 Minhas Memórias", callback_data="menu:memorias"),
        ],
        [
            InlineKeyboardButton("📄 Exportar Chat (PDF)", callback_data="menu:exportar"),
            InlineKeyboardButton("🧹 Novo Chat", callback_data="menu:limpar"),
        ],
        [
            InlineKeyboardButton("📊 Telemetria & Status", callback_data="menu:status"),
            InlineKeyboardButton("🎨 Criar Imagem HD", callback_data="menu:img_help"),
        ],
    ]

    if is_admin(user_id):
        keyboard.append([
            InlineKeyboardButton("🎛️ Master Admin Control", callback_data="admin:main")
        ])

    keyboard.append([
        InlineKeyboardButton("❓ Guia Completo de Comandos", callback_data="menu:ajuda")
    ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    menu_text = (
        "✨ *BrainBot AI Enterprise* • `v3.0`\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"🤖 *Motor Ativo:* {model_name}\n"
        f"🎙️ *Modo Voz:* `{voice_status}` | ⭐ *Plano:* `{user.get('tier', 'free').upper()}`\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Como posso te ajudar hoje? Escolha uma ação rápida abaixo ou converse diretamente no chat:"
    )

    await safe_reply(update, menu_text, reply_markup=reply_markup)

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cmd_menu(update, context)

async def cmd_modelos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /modelos para alternar entre os motores do Top 4."""
    user_id = update.effective_user.id
    if not is_authorized(user_id): return

    keyboard = [
        [
            InlineKeyboardButton("✨ Auto (Roteamento Dinâmico)", callback_data="set_model:auto"),
        ],
        [
            InlineKeyboardButton("⚡ DeepSeek V4/V3 (Código & Texto)", callback_data="set_model:deepseek"),
        ],
        [
            InlineKeyboardButton("🧠 DeepSeek R1 (Raciocínio Profundo)", callback_data="set_model:deepseek-r1"),
        ],
        [
            InlineKeyboardButton("⚡ Gemini 3.6 Flash (Google AI)", callback_data="set_model:gemini"),
        ],
        [
            InlineKeyboardButton("🚀 GPT-OSS 120B (Groq 300+ tok/s)", callback_data="set_model:groq-llama"),
        ],
        [
            InlineKeyboardButton("🟢 GPT-4o Oficial (GitHub/Azure)", callback_data="set_model:github-gpt4o"),
        ],
        [
            InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="menu:main")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = (
        "⚙️ *SELEÇÃO DE MOTOR DE INTELIGÊNCIA ARTIFICIAL*\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "Selecione o motor desejado para suas conversas ou ative o modo **Auto** para balanceamento automático:"
    )
    await safe_reply(update, text, reply_markup=reply_markup)

async def cmd_assistentes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menu de Assistentes Especialistas (GPTs Prontos)."""
    user_id = update.effective_user.id
    if not is_authorized(user_id): return

    keyboard = [
        [InlineKeyboardButton("👨‍💻 Tech Lead & Arquiteto Sênior", callback_data="set_asst:dev_lead")],
        [InlineKeyboardButton("📈 Analista Financeiro & Investimentos", callback_data="set_asst:finance")],
        [InlineKeyboardButton("✍️ Copywriter & Criador de Conteúdo", callback_data="set_asst:copywriter")],
        [InlineKeyboardButton("⚖️ Auditor Jurídico & Contratos", callback_data="set_asst:legal")],
        [InlineKeyboardButton("🇬🇧 Professor de Inglês Interativo", callback_data="set_asst:english_tutor")],
        [InlineKeyboardButton("🔄 Restaurar Assistente Geral Padrão", callback_data="set_asst:default")],
        [InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="menu:main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        "🎭 *ESPECIALISTAS & PERSONAS PROFISSIONAIS (GPTS)*\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "Escolha um perfil especializado para transformar o comportamento do BrainBot com 1 clique:"
    )
    await safe_reply(update, text, reply_markup=reply_markup)

async def cmd_voz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ativa ou desativa as respostas faladas em áudio (Text-to-Speech)."""
    user_id = update.effective_user.id
    if not is_authorized(user_id): return

    new_state = await db.toggle_voice_mode(user_id)
    state_str = "🔊 *Ativado!* A partir de agora o bot responderá com mensagens de voz." if new_state else "🔇 *Desativado!* O bot responderá apenas por texto."
    
    if update.callback_query:
        back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="menu:main")]])
        await safe_reply(update, f"🎙️ **Modo de Voz:** {state_str}", reply_markup=back_kb)
    else:
        await safe_reply(update, f"🎙️ **Modo de Voz:** {state_str}")

async def cmd_lembrar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Grava uma memória permanente de longo prazo sobre o usuário."""
    user_id = update.effective_user.id
    if not is_authorized(user_id): return

    memory_text = " ".join(context.args)
    if not memory_text:
        await safe_reply(update, "ℹ️ *Uso:* `/lembrar eu uso Linux Mint e programo em Python e Rust`")
        return

    await db.add_memory(user_id, memory_text)
    await safe_reply(update, f"🧠 *Memória guardada com sucesso!*\n\n_\"{memory_text}\"_\n\nO BrainBot lembrará disso em todas as conversas futuras.")

async def cmd_memorias(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lista e gerencia memórias salvas do usuário."""
    user_id = update.effective_user.id
    if not is_authorized(user_id): return

    memories = await db.get_memories(user_id)
    if not memories:
        text = "🧠 *Nenhuma memória personalizada salva ainda.*\n\nPara gravar algo, digite:\n`/lembrar [fato sobre você]`"
        back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="menu:main")]])
        await safe_reply(update, text, reply_markup=back_kb)
        return

    lines = ["🧠 *MEMÓRIAS DE LONGO PRAZO SALVAS:*\n━━━━━━━━━━━━━━━━━━━━━"]
    for m in memories:
        lines.append(f"• `[ID {m['id']}]` {m['memory_text']}")

    lines.append("\n_Para apagar tudo, use o botão abaixo:_")
    keyboard = [
        [InlineKeyboardButton("🗑️ Apagar Todas as Memórias", callback_data="memories:clear_all")],
        [InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="menu:main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await safe_reply(update, "\n".join(lines), reply_markup=reply_markup)

async def cmd_exportar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menu para exportar histórico da conversa."""
    user_id = update.effective_user.id
    if not is_authorized(user_id): return

    keyboard = [
        [
            InlineKeyboardButton("📄 Exportar como PDF", callback_data="export:pdf"),
            InlineKeyboardButton("📝 Exportar como Markdown", callback_data="export:md"),
        ],
        [
            InlineKeyboardButton("📋 Exportar como TXT", callback_data="export:txt"),
            InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="menu:main"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = (
        "📑 *EXPORTAÇÃO DO HISTÓRICO DA CONVERSA*\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "Escolha o formato no qual deseja baixar todo o relatório da conversa atual:"
    )
    await safe_reply(update, text, reply_markup=reply_markup)

async def cmd_limpar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id): return
    await db.clear_history(user_id)
    text = "🧹 *Memória da conversa reiniciada!*\nUm novo chat limpo foi iniciado."
    if update.callback_query:
        back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="menu:main")]])
        await safe_reply(update, text, reply_markup=back_kb)
    else:
        await safe_reply(update, text)

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
        f"🎙️ *Modo Voz:* `{'Ativo' if user.get('voice_mode_enabled') else 'Desativado'}`\n"
        f"🔒 *Acesso:* `{settings.ACCESS_MODE}` | ⭐ *Plano:* `{user.get('tier', 'free').upper()}`\n"
        f"🩺 *Healthcheck:* `http://localhost:8080/health` (Healthy)"
    )
    
    if update.callback_query:
        back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="menu:main")]])
        await safe_reply(update, status_text, reply_markup=back_kb)
    else:
        await safe_reply(update, status_text)

async def cmd_web(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id): return

    query = " ".join(context.args)
    if not query:
        await safe_reply(update, "ℹ️ *Uso:* `/web últimas notícias sobre tecnologia`")
        return

    from app.handlers.messages import stream_chat_response
    await stream_chat_response(update, context, query, user_id)

async def cmd_imagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id): return

    prompt = " ".join(context.args)
    if not prompt:
        await safe_reply(update, "ℹ️ *Uso:* `/imagem um dragão mecânico futurista 8k`")
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_PHOTO)
    msg_wait = await update.message.reply_text("🎨 *Renderizando imagem com Flux.1...*", parse_mode=ParseMode.MARKDOWN)

    url_img = image_generator.get_image_url(prompt)
    await db.record_usage(user_id, "image_gen")

    try:
        await update.message.reply_photo(
            photo=url_img,
            caption=f"🎨 *Prompt:* _{prompt}_\n\n▫️ _Flux.1 HD_",
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
        await safe_reply(update, "🔄 Personalidade redefinida para o padrão.")
        return

    await db.update_user_system_prompt(user_id, custom_p)
    await safe_reply(update, f"🎭 Personalidade atualizada:\n_{custom_p}_")

def register_commands(app: Application):
    app.add_handler(CommandHandler("menu", cmd_menu))
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_menu))
    app.add_handler(CommandHandler("ajuda", cmd_menu))
    app.add_handler(CommandHandler("modelos", cmd_modelos))
    app.add_handler(CommandHandler("assistentes", cmd_assistentes))
    app.add_handler(CommandHandler("voz", cmd_voz))
    app.add_handler(CommandHandler("lembrar", cmd_lembrar))
    app.add_handler(CommandHandler("memorias", cmd_memorias))
    app.add_handler(CommandHandler("exportar", cmd_exportar))
    app.add_handler(CommandHandler("limpar", cmd_limpar))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("web", cmd_web))
    app.add_handler(CommandHandler("imagem", cmd_imagem))
    app.add_handler(CommandHandler("prompt", cmd_prompt))
