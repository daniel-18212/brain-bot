"""
Media Handlers: Photos (Vision), Audio/Voice Notes, and Documents (PDFs, Code) with Animated Loading Frames.
"""
import io
import logging
from telegram import Update
from telegram.constants import ParseMode, ChatAction
from telegram.ext import Application, MessageHandler, ContextTypes, filters
from app.config import settings
from app.database import db
from app.core import vision_analyzer, audio_transcriber, document_parser, AnimatedLoader
from app.handlers.messages import stream_chat_response
from app.handlers.commands import show_unauthorized_card

logger = logging.getLogger(__name__)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await db.is_user_authorized(user_id):
        await show_unauthorized_card(update, context)
        return

    allowed, current_count, max_quota, tier = await db.check_and_increment_quota(user_id)
    if not allowed:
        await update.message.reply_text(f"⚠️ Limite diário de {max_quota} mensagens atingido para o plano {tier.upper()}.", parse_mode=ParseMode.MARKDOWN)
        return

    caption = update.message.caption or "Descreva e analise detalhadamente esta imagem:"
    photo = update.message.photo[-1]

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    msg_status = await update.message.reply_text("👁️ *Carregando imagem...*", parse_mode=ParseMode.MARKDOWN)
    loader = AnimatedLoader(msg_status, preset="vision", interval=1.2).start()

    try:
        photo_file = await context.bot.get_file(photo.file_id)
        buffer = io.BytesIO()
        await photo_file.download_to_memory(buffer)
        buffer.seek(0)

        analysis = await vision_analyzer.analyze_image(buffer, prompt=caption)
        await db.record_usage(user_id, "vision")
        
        await db.save_message(user_id, "user", f"[Foto enviada] {caption}")
        await db.save_message(user_id, "assistant", analysis)

        await loader.stop()
        resp_text = f"{analysis}\n\n▫️ _⚡ Gemini 3.6 Flash (Vision)_"
        await msg_status.edit_text(resp_text, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await loader.stop()
        logger.error(f"Erro no processamento de foto: {e}")
        await msg_status.edit_text(f"❌ Erro ao analisar imagem: `{e}`", parse_mode=ParseMode.MARKDOWN)

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await db.is_user_authorized(user_id):
        await show_unauthorized_card(update, context)
        return

    voice = update.message.voice or update.message.audio
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.RECORD_VOICE)
    msg_status = await update.message.reply_text("🎙️ *Ouvindo áudio...*", parse_mode=ParseMode.MARKDOWN)
    loader = AnimatedLoader(msg_status, preset="voice", interval=1.2).start()

    try:
        voice_file = await context.bot.get_file(voice.file_id)
        buffer = io.BytesIO()
        await voice_file.download_to_memory(buffer)
        buffer.seek(0)

        transcription = await audio_transcriber.transcribe(buffer)
        await db.record_usage(user_id, "audio")

        await loader.stop()
        await msg_status.edit_text(f"🗣️ *Você disse:* _{transcription}_", parse_mode=ParseMode.MARKDOWN)

        await stream_chat_response(update, context, transcription, user_id, is_voice_input=True)

    except Exception as e:
        await loader.stop()
        logger.error(f"Erro no áudio: {e}")
        await msg_status.edit_text(f"❌ Erro ao processar áudio: `{e}`", parse_mode=ParseMode.MARKDOWN)

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await db.is_user_authorized(user_id):
        await show_unauthorized_card(update, context)
        return

    doc = update.message.document
    caption = update.message.caption or "Faça uma leitura completa e análise detalhada deste arquivo:"

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    msg_status = await update.message.reply_text(f"📑 *Abrindo documento:* `{doc.file_name}`...", parse_mode=ParseMode.MARKDOWN)
    loader = AnimatedLoader(msg_status, preset="document", interval=1.2).start()

    try:
        file = await context.bot.get_file(doc.file_id)
        file_bytes = await file.download_as_bytearray()

        extracted_text = document_parser.extract_text(file_bytes, doc.file_name)
        await db.record_usage(user_id, "document")

        prompt = (
            f"[ARQUIVO ANEXADO PELO USUÁRIO: {doc.file_name}]\n\n"
            f"{extracted_text}\n\n"
            f"[SOLICITAÇÃO DO USUÁRIO]: {caption}"
        )

        await loader.stop()
        await msg_status.edit_text(f"✅ *Documento lido com sucesso:* `{doc.file_name}`", parse_mode=ParseMode.MARKDOWN)

        await stream_chat_response(update, context, prompt, user_id)

    except Exception as e:
        await loader.stop()
        logger.error(f"Erro no documento: {e}")
        await msg_status.edit_text(f"❌ Erro ao ler documento: `{e}`", parse_mode=ParseMode.MARKDOWN)

def register_media(app: Application):
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
