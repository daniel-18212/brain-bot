"""
Text Message Handler with Live Streaming and Smart Context Management.
"""
import asyncio
import logging
import time
from telegram import Update
from telegram.constants import ParseMode, ChatAction
from telegram.error import BadRequest
from telegram.ext import Application, MessageHandler, ContextTypes, filters
from app.config import settings
from app.database import db
from app.core import llm_router

logger = logging.getLogger(__name__)

def is_authorized(user_id: int) -> bool:
    if settings.ACCESS_MODE == "PRIVATE":
        return user_id == settings.ADMIN_USER_ID
    elif settings.ACCESS_MODE == "WHITELIST":
        return user_id in settings.WHITELIST_USERS
    return True

async def stream_chat_response(update: Update, context: ContextTypes.DEFAULT_TYPE, user_prompt: str, user_id: int):
    """Executa a resposta ao vivo com streaming e throttle inteligente."""
    user = await db.get_or_create_user(user_id)
    history = await db.get_context_history(user_id)
    
    # Monta a lista de mensagens para o roteador
    messages = history + [{"role": "user", "content": user_prompt}]
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    msg_status = await update.message.reply_text("🤔 *Pensando...*", parse_mode=ParseMode.MARKDOWN)
    
    last_update = time.time()
    accumulated_text = ""
    accumulated_reasoning = ""
    selected_model = user["selected_model"]
    custom_sys = user.get("custom_system_prompt")

    try:
        async for text_chunk, reasoning_chunk in llm_router.stream_response(
            model_key=selected_model,
            messages=messages,
            system_prompt=custom_sys
        ):
            accumulated_text = text_chunk
            if reasoning_chunk:
                accumulated_reasoning = reasoning_chunk

            now = time.time()
            if now - last_update >= settings.STREAMING_THROTTLE_SECONDS and accumulated_text.strip():
                display = accumulated_text
                if accumulated_reasoning:
                    display = f"💭 _Pensando:_\n`{accumulated_reasoning[-250:]}`\n\n{accumulated_text}"
                
                # Trunca preview para não exceder 4000
                if len(display) > 4000:
                    display = display[:3990] + "..."

                try:
                    await msg_status.edit_text(display, parse_mode=ParseMode.MARKDOWN)
                    last_update = now
                except BadRequest:
                    pass

        # Finalização da Mensagem Completa
        if accumulated_text.strip():
            # Salva no banco de dados SQLite
            await db.save_message(user_id, "user", user_prompt, selected_model)
            await db.save_message(user_id, "assistant", accumulated_text, selected_model)
            await db.record_usage(user_id, "text", selected_model)

            # Envia sem estourar limites de 4096 caracteres
            if len(accumulated_text) <= 4090:
                try:
                    await msg_status.edit_text(accumulated_text, parse_mode=ParseMode.MARKDOWN)
                except Exception:
                    await msg_status.edit_text(accumulated_text)
            else:
                await msg_status.delete()
                for i in range(0, len(accumulated_text), 4000):
                    chunk = accumulated_text[i:i+4000]
                    try:
                        await update.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN)
                    except Exception:
                        await update.message.reply_text(chunk)

    except Exception as e:
        logger.error(f"Erro no processamento de texto: {e}")
        await msg_status.edit_text(f"❌ Ocorreu um erro: `{e}`", parse_mode=ParseMode.MARKDOWN)

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id): return
    
    text = update.message.text
    if not text: return
    
    await stream_chat_response(update, context, text, user_id)

def register_messages(app: Application):
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
