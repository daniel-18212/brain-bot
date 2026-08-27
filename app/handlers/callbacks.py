"""
Telegram Inline Button Callback Query Handlers.
"""
import logging
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CallbackQueryHandler, ContextTypes
from app.database import db
from app.core import llm_router

logger = logging.getLogger(__name__)

async def callback_model_switch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    data = query.data

    if data.startswith("set_model:"):
        model_key = data.split(":", 1)[1]
        model_info = llm_router.AVAILABLE_MODELS.get(model_key)
        
        if not model_info:
            await query.edit_message_text("❌ Modelo não reconhecido.")
            return

        await db.update_user_model(user_id, model_key)
        
        confirmation = (
            f"✅ *Modelo Ativado com Sucesso!*\n\n"
            f"🤖 *Nome:* {model_info['name']}\n"
            f"🏢 *Provedor:* {model_info['provider']}\n"
            f"📝 *Detalhes:* _{model_info['description']}_"
        )
        await query.edit_message_text(confirmation, parse_mode=ParseMode.MARKDOWN)

def register_callbacks(app: Application):
    app.add_handler(CallbackQueryHandler(callback_model_switch, pattern="^set_model:"))
