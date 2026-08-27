"""
Main Application Entrypoint and Lifecycle Manager.
"""
import logging
import sys
from telegram.ext import ApplicationBuilder
from app.config import settings
from app.database import db
from app.handlers import (
    register_commands,
    register_callbacks,
    register_messages,
    register_media
)

# Configuração de Logs
logging.basicConfig(
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("BrainBot")

async def post_init(application) -> None:
    """Executado após a conexão inicial do bot com a API do Telegram."""
    await db.init_db()
    bot_info = await application.bot.get_me()
    logger.info(f"🚀 BrainBot conectado com sucesso como @{bot_info.username} (ID: {bot_info.id})")
    logger.info(f"🔒 Modo de Acesso Ativo: {settings.ACCESS_MODE}")
    logger.info(f"🧠 Modelo Padrão: {settings.DEFAULT_MODEL}")

async def global_error_handler(update, context) -> None:
    """Captura e registra exceções não tratadas sem derrubar o bot."""
    logger.error(f"⚠️ Exceção não tratada ao processar update {update}: {context.error}", exc_info=context.error)

def main():
    logger.info("Iniciando BrainBot Enterprise...")
    try:
        settings.validate()
    except ValueError as e:
        logger.error(f"Erro de Validação de Configurações: {e}")
        sys.exit(1)

    app = (
        ApplicationBuilder()
        .token(settings.TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .concurrent_updates(True)
        .build()
    )

    # Registro de Handlers
    register_commands(app)
    register_callbacks(app)
    register_media(app)
    register_messages(app)

    # Tratamento de Erros Global
    app.add_error_handler(global_error_handler)

    # Inicia o Long Polling
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
