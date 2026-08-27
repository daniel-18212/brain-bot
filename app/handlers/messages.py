"""
Text Message Handler with Live Streaming, Auto Web-Search Grounding, and Model Footer Badges.
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
from app.core import llm_router, web_search_engine

logger = logging.getLogger(__name__)

def is_authorized(user_id: int) -> bool:
    if settings.ACCESS_MODE == "PRIVATE":
        return user_id == settings.ADMIN_USER_ID
    elif settings.ACCESS_MODE == "WHITELIST":
        return user_id in settings.WHITELIST_USERS
    return True

async def keep_typing_alive(bot, chat_id: int, stop_event: asyncio.Event):
    """Mantém a indicação de 'digitando...' ativa no topo do chat do Telegram."""
    try:
        while not stop_event.is_set():
            await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            await asyncio.sleep(3)
    except Exception:
        pass

async def stream_chat_response(update: Update, context: ContextTypes.DEFAULT_TYPE, user_prompt: str, user_id: int):
    """Executa a resposta ao vivo com auto-busca na web, streaming e rodapé com identificador de modelo."""
    user = await db.get_or_create_user(user_id)
    history = await db.get_context_history(user_id)
    selected_model = user["selected_model"]
    custom_sys = user.get("custom_system_prompt")
    chat_id = update.effective_chat.id

    stop_typing_event = asyncio.Event()
    typing_task = asyncio.create_task(keep_typing_alive(context.bot, chat_id, stop_typing_event))

    msg_status = await update.message.reply_text("✨ *Processando sua mensagem...*", parse_mode=ParseMode.MARKDOWN)

    # 1. Detecção Inteligente de Busca na Web (Auto Web Grounding)
    final_prompt = user_prompt
    if web_search_engine.should_trigger_search(user_prompt):
        try:
            await msg_status.edit_text("🌐 *Consultando a internet em tempo real...*", parse_mode=ParseMode.MARKDOWN)
            web_data = await web_search_engine.search(user_prompt, max_results=4)
            await db.record_usage(user_id, "web_search")
            final_prompt = (
                f"[DADOS EM TEMPO REAL DA WEB]:\n{web_data}\n\n"
                f"[PERGUNTA DO USUÁRIO]:\n{user_prompt}\n\n"
                "Responda à pergunta do usuário utilizando as informações mais recentes da web acima."
            )
        except Exception as e:
            logger.warning(f"Falha na auto-busca web: {e}")

    messages = history + [{"role": "user", "content": final_prompt}]
    
    last_update = time.time()
    accumulated_text = ""
    accumulated_reasoning = ""
    actual_model_used = selected_model
    fallback_alert = ""

    try:
        async for text_chunk, reasoning_chunk, current_model, fb_notice in llm_router.stream_response(
            model_key=selected_model,
            messages=messages,
            system_prompt=custom_sys
        ):
            accumulated_text = text_chunk
            actual_model_used = current_model
            if fb_notice:
                fallback_alert = fb_notice
            if reasoning_chunk:
                accumulated_reasoning = reasoning_chunk

            now = time.time()
            if now - last_update >= settings.STREAMING_THROTTLE_SECONDS and accumulated_text.strip():
                display = accumulated_text
                if accumulated_reasoning:
                    display = f"💭 _Raciocínio:_\n`{accumulated_reasoning[-200:]}`\n\n{accumulated_text}"
                
                if len(display) > 4000:
                    display = display[:3990] + "..."

                try:
                    await msg_status.edit_text(display, parse_mode=ParseMode.MARKDOWN)
                    last_update = now
                except BadRequest:
                    pass

        stop_typing_event.set()
        await typing_task

        if accumulated_text.strip():
            # Salva no histórico do banco SQLite
            await db.save_message(user_id, "user", user_prompt, actual_model_used)
            await db.save_message(user_id, "assistant", accumulated_text, actual_model_used)
            await db.record_usage(user_id, "text", actual_model_used)

            # Formata o Rodapé Sutil com o Badge do Modelo
            model_badge = llm_router.AVAILABLE_MODELS.get(actual_model_used, {}).get("badge", actual_model_used)
            footer = f"\n\n▫️ _{model_badge}_"
            if fallback_alert:
                footer = f"\n\n{fallback_alert}\n▫️ _{model_badge}_"

            final_text = accumulated_text.strip() + footer

            if len(final_text) <= 4090:
                try:
                    await msg_status.edit_text(final_text, parse_mode=ParseMode.MARKDOWN)
                except Exception:
                    await msg_status.edit_text(final_text)
            else:
                await msg_status.delete()
                for i in range(0, len(final_text), 4000):
                    chunk = final_text[i:i+4000]
                    try:
                        await update.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN)
                    except Exception:
                        await update.message.reply_text(chunk)

    except Exception as e:
        stop_typing_event.set()
        logger.error(f"Erro no processamento de texto: {e}")
        await msg_status.edit_text(f"❌ Ocorreu um erro ao processar sua resposta: `{e}`", parse_mode=ParseMode.MARKDOWN)

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id): return
    
    text = update.message.text
    if not text: return
    
    await stream_chat_response(update, context, text, user_id)

def register_messages(app: Application):
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
