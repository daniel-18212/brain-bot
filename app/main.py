"""
Institutional Application Entrypoint, Anti-Crash Supervisor, and Lifecycle Manager.
"""
import asyncio
import logging
import signal
import sys
from telegram import BotCommand
from telegram.ext import ApplicationBuilder
from app.config import settings
from app.database import db
from app.core.health import start_health_server
from app.handlers import (
    register_commands,
    register_callbacks,
    register_messages,
    register_media,
    register_admin
)

logging.basicConfig(
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("BrainBotMaster")

async def post_init(application) -> None:
    """Executado após conexão bem-sucedida com a infraestrutura do Telegram."""
    await db.init_db()
    
    # Inicia o Servidor HTTP de Healthcheck na porta 8080
    health_port = int(getattr(settings, "HEALTH_PORT", 8080))
    await start_health_server(host="0.0.0.0", port=health_port)

    # Configura o Menu Nativo de Comandos no Telegram
    bot_commands = [
        BotCommand("menu", "Menu Principal com todos os recursos"),
        BotCommand("modelos", "Alternar Motor de IA"),
        BotCommand("limpar", "Novo Chat (Zerar Memória)"),
        BotCommand("web", "Pesquisa na Web em Tempo Real"),
        BotCommand("imagem", "Gerar Imagem HD (Flux.1)"),
        BotCommand("status", "Status da Sessão e Hardware"),
        BotCommand("prompt", "Personalizar Persona da IA"),
        BotCommand("admin", "Painel de Controle Master (Admin)"),
        BotCommand("ajuda", "Guia Completo de Comandos"),
    ]
    try:
        await application.bot.set_my_commands(bot_commands)
        logger.info("📱 Menu nativo de comandos registrado com sucesso no Telegram.")
    except Exception as e:
        logger.warning(f"Aviso ao registrar comandos nativos: {e}")

    # Carrega configurações dinâmicas salvas no banco
    saved_mode = await db.get_system_setting("ACCESS_MODE", settings.ACCESS_MODE)
    settings.ACCESS_MODE = saved_mode

    bot_info = await application.bot.get_me()
    logger.info("=" * 60)
    logger.info(f"🚀 BRAIN-BOT INSTITUCIONAL ONLINE: @{bot_info.username} (ID: {bot_info.id})")
    logger.info(f"🔒 Modo de Acesso Ativo: {settings.ACCESS_MODE}")
    logger.info(f"👑 Master Admin ID: {settings.ADMIN_USER_ID}")
    logger.info(f"🧠 Modelo Padrão: {settings.DEFAULT_MODEL}")
    logger.info(f"🩺 Health Endpoint: http://0.0.0.0:{health_port}/health")
    logger.info("=" * 60)

async def global_error_handler(update, context) -> None:
    """Supervisor Global de Exceções: Garante que o bot seja anticrash."""
    logger.error(f"⚠️ [SUPERVISOR ANTICRASH] Exceção capturada no update {update}: {context.error}", exc_info=context.error)

def main():
    logger.info("Iniciando BrainBot em modo de alta disponibilidade...")
    try:
        settings.validate()
    except ValueError as e:
        logger.error(f"❌ Falha de Inicialização: {e}")
        sys.exit(1)

    app = (
        ApplicationBuilder()
        .token(settings.TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .concurrent_updates(True)
        .build()
    )

    # Registro de Todos os Controladores
    register_commands(app)
    register_callbacks(app)
    register_media(app)
    register_admin(app)
    register_messages(app)

    # Supervisor Global de Falhas
    app.add_error_handler(global_error_handler)

    logger.info("Iniciando Long Polling com recuperação automática...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
