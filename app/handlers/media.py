"""
Media Handlers: Photos (Vision), Audio/Voice Notes, and Documents (PDFs, Code).
"""
import io
import logging
from telegram import Update
from telegram.constants import ParseMode, ChatAction
from telegram.ext import Application, MessageHandler, ContextTypes, filters
from app.config import settings
from app.database import db
from app.core import vision_analyzer, audio_transcriber, document_parser
from app.handlers.messages import stream_chat_response

logger = logging.getLogger(__name__)

def is_authorized(user_id: int) -> bool:
    if settings.ACCESS_MODE == "PRIVATE":
        return user_id == settings.ADMIN_USER_ID
    elif settings.ACCESS_MODE == "WHITELIST":
        return user_id in settings.WHITELIST_USERS
    return True

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id): return

    caption = update.message.caption or "Analise esta imagem em detalhes e descreva o que observa:"
    photo = update.message.photo[-1]  # Maior resolução disponível

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    msg_status = await update.message.reply_text("👁️ *Analisando imagem com Visão Computacional...*", parse_mode=ParseMode.MARKDOWN)

    try:
        photo_file = await context.bot.get_file(photo.file_id)
        buffer = io.BytesIO()
        await photo_file.download_to_memory(buffer)
        buffer.seek(0)

        analysis = await vision_analyzer.analyze_image(buffer, prompt=caption)
        await db.record_usage(user_id, "vision")
        
        # Salva o contexto
        await db.save_message(user_id, "user", f"[Foto enviada] {caption}")
        await db.save_message(user_id, "assistant", analysis)

        await msg_status.edit_text(analysis, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"Erro no processamento de foto: {e}")
        await msg_status.edit_text(f"❌ Erro ao analisar imagem: `{e}`", parse_mode=ParseMode.MARKDOWN)

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id): return

    voice = update.message.voice or update.message.audio
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.RECORD_VOICE)
    msg_status = await update.message.reply_text("🎙️ *Transcrevendo áudio via Groq Whisper...*", parse_mode=ParseMode.MARKDOWN)

    try:
        voice_file = await context.bot.get_file(voice.file_id)
        buffer = io.BytesIO()
        await voice_file.download_to_memory(buffer)
        buffer.seek(0)

        transcription = await audio_transcriber.transcribe(buffer)
        await db.record_usage(user_id, "audio")

        await msg_status.edit_text(f"🗣️ *Você disse:* _{transcription}_", parse_mode=ParseMode.MARKDOWN)

        # Envia a transcrição para a IA responder
        await stream_chat_response(update, context, transcription, user_id)

    except Exception as e:
        logger.error(f"Erro no áudio: {e}")
        await msg_status.edit_text(f"❌ Erro ao processar áudio: `{e}`", parse_mode=ParseMode.MARKDOWN)

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id): return

    doc = update.message.document
    caption = update.message.caption or "Analise, resuma e extraia os pontos mais importantes deste arquivo:"

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    msg_status = await update.message.reply_text(f"📄 *Processando documento ({doc.file_name})...*", parse_mode=ParseMode.MARKDOWN)

    try:
        file = await context.bot.get_file(doc.file_id)
        file_bytes = await file.download_as_bytearray()

        extracted_text = document_parser.extract_text(file_bytes, doc.file_name)
        await db.record_usage(user_id, "document")

        prompt = f"{caption}\n\n[ARQUIVO: {doc.file_name}]\n{extracted_text}"
        await msg_status.delete()

        await stream_chat_response(update, context, prompt, user_id)

    except Exception as e:
        logger.error(f"Erro no documento: {e}")
        await msg_status.edit_text(f"❌ Erro ao processar arquivo: `{e}`", parse_mode=ParseMode.MARKDOWN)

def register_media(app: Application):
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
