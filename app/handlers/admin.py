"""
Institutional Admin Control Panel & Master Management Center for Telegram.
"""
import asyncio
import io
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode, ChatAction
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from app.config import settings
from app.database import db
from app.core.resilience import telemetry, circuit_breaker

logger = logging.getLogger(__name__)

def is_admin(user_id: int) -> bool:
    return user_id == settings.ADMIN_USER_ID

async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Painel Principal de Administração."""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ Acesso Restrito: Apenas administradores do sistema.")
        return

    keyboard = [
        [
            InlineKeyboardButton("📊 Telemetria do Servidor", callback_data="admin:telemetry"),
            InlineKeyboardButton("📈 Métricas de Negócio (SaaS)", callback_data="admin:metrics"),
        ],
        [
            InlineKeyboardButton("👥 Top Usuários & Cotas", callback_data="admin:users"),
            InlineKeyboardButton("🔒 Alternar Modo de Acesso", callback_data="admin:access_mode"),
        ],
        [
            InlineKeyboardButton("💾 Fazer Backup do Banco (.sqlite)", callback_data="admin:backup"),
            InlineKeyboardButton("🔄 Recarregar Configurações", callback_data="admin:reload"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    admin_dashboard_text = (
        "🎛️ *PAINEL DE CONTROLE INSTITUCIONAL (MASTER ADMIN)*\n\n"
        "Bem-vindo ao Centro de Controle do BrainBot.\n"
        "Selecione uma opção abaixo para monitorar, configurar ou gerenciar o sistema em tempo real."
    )
    await update.message.reply_text(admin_dashboard_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

async def callback_admin_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Trata cliques nos botões do painel de administração."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    if not is_admin(user_id): return

    action = query.data

    # 1. Telemetria do Servidor
    if action == "admin:telemetry":
        m = telemetry.get_metrics()
        text = (
            "🖥️ *TELEMETRIA DO SERVIDOR EM TEMPO REAL*\n\n"
            f"⚡ *CPU:* `{m['cpu_percent']}%`\n"
            f"🧠 *RAM:* `{m['ram_used_mb']:.1f} MB / {m['ram_total_mb']:.1f} MB` ({m['ram_percent']}%)\n"
            f"💽 *Disco:* `{m['disk_used_gb']:.1f} GB / {m['disk_total_gb']:.1f} GB` ({m['disk_percent']}%)\n"
            f"🗄️ *Tamanho do Banco SQLite:* `{m['db_size_mb']} MB`\n"
            f"⏱️ *Uptime do Processo:* `{m['uptime']}`"
        )
        back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="admin:main")]])
        await query.edit_message_text(text, reply_markup=back_kb, parse_mode=ParseMode.MARKDOWN)

    # 2. Métricas de Negócio
    elif action == "admin:metrics":
        stats = await db.get_admin_dashboard_stats()
        text = (
            "📈 *MÉTRICAS DE NEGÓCIO & USO (SAAS)*\n\n"
            f"👥 *Total de Usuários Cadastrados:* `{stats['total_users']}`\n"
            f"🟢 *Usuários Ativos:* `{stats['active_users']}`\n"
            f"⭐ *Assinantes Pro / Ilimitados:* `{stats['pro_users']}`\n"
            f"💬 *Total de Mensagens:* `{stats['total_messages']}`\n"
            f"📅 *Mensagens Hoje:* `{stats['messages_today']}`\n"
            f"🎨 *Imagens Geradas:* `{stats['images_gen']}`\n"
            f"🌐 *Buscas na Web:* `{stats['web_searches']}`"
        )
        back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="admin:main")]])
        await query.edit_message_text(text, reply_markup=back_kb, parse_mode=ParseMode.MARKDOWN)

    # 3. Top Usuários
    elif action == "admin:users":
        top = await db.get_top_users(limit=8)
        lines = ["👥 *TOP USUÁRIOS POR CONSUMO DE MENSAGENS:*\n"]
        for idx, u in enumerate(top, start=1):
            uname = f"@{u['username']}" if u['username'] else u['first_name'] or "Sem Nome"
            status_icon = "🟢" if u['status'] == "active" else "🔴"
            lines.append(f"{idx}. {status_icon} *{uname}* (ID: `{u['user_id']}`) | Tier: `{u['tier'].upper()}` | Msgs: `{u['message_count']}`")

        lines.append("\n💡 *Comandos Rápidos:*\n• `/promover <ID> <free|pro|unlimited>`\n• `/ban <ID>` | `/unban <ID>`")
        text = "\n".join(lines)
        back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="admin:main")]])
        await query.edit_message_text(text, reply_markup=back_kb, parse_mode=ParseMode.MARKDOWN)

    # 4. Alternar Modo de Acesso
    elif action == "admin:access_mode":
        current = settings.ACCESS_MODE
        modes = ["PUBLIC", "WHITELIST", "PRIVATE"]
        next_mode = modes[(modes.index(current) + 1) % len(modes)]
        settings.ACCESS_MODE = next_mode
        await db.set_system_setting("ACCESS_MODE", next_mode)
        
        text = f"🔒 *Modo de Acesso Alterado!*\n\nNovo modo ativo: `{next_mode}`\n(Sem necessidade de reiniciar o servidor)."
        back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="admin:main")]])
        await query.edit_message_text(text, reply_markup=back_kb, parse_mode=ParseMode.MARKDOWN)

    # 5. Backup do Banco SQLite
    elif action == "admin:backup":
        await query.edit_message_text("💾 *Gerando cópia de segurança do banco de dados...*", parse_mode=ParseMode.MARKDOWN)
        if settings.DATABASE_PATH.exists():
            with open(settings.DATABASE_PATH, "rb") as f:
                await context.bot.send_document(
                    chat_id=user_id,
                    document=f,
                    filename=f"backup_brainbot_{datetime_now_str()}.sqlite",
                    caption="💾 *Backup do Banco de Dados SQLite Concluído!*"
                )
        else:
            await query.edit_message_text("❌ Arquivo de banco de dados não encontrado.")

    # Voltar ao Menu Principal
    elif action == "admin:main":
        keyboard = [
            [
                InlineKeyboardButton("📊 Telemetria do Servidor", callback_data="admin:telemetry"),
                InlineKeyboardButton("📈 Métricas de Negócio (SaaS)", callback_data="admin:metrics"),
            ],
            [
                InlineKeyboardButton("👥 Top Usuários & Cotas", callback_data="admin:users"),
                InlineKeyboardButton("🔒 Alternar Modo de Acesso", callback_data="admin:access_mode"),
            ],
            [
                InlineKeyboardButton("💾 Fazer Backup do Banco (.sqlite)", callback_data="admin:backup"),
                InlineKeyboardButton("🔄 Recarregar Configurações", callback_data="admin:reload"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("🎛️ *PAINEL DE CONTROLE INSTITUCIONAL*", reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

def datetime_now_str() -> str:
    from datetime import datetime
    return datetime.now().strftime("%Y%m%d_%H%M%S")

# --- Comandos Extras de Administração ---

async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Transmite uma mensagem global para todos os usuários cadastrados."""
    user_id = update.effective_user.id
    if not is_admin(user_id): return

    msg_text = " ".join(context.args)
    if not msg_text:
        await update.message.reply_text("ℹ️ *Uso:* `/broadcast Olá a todos! Nova funcionalidade adicionada...`", parse_mode=ParseMode.MARKDOWN)
        return

    users = await db.get_all_users_for_broadcast()
    await update.message.reply_text(f"📢 *Iniciando transmissão para {len(users)} usuários...*", parse_mode=ParseMode.MARKDOWN)

    success_count = 0
    fail_count = 0

    for uid in users:
        try:
            await context.bot.send_message(chat_id=uid, text=f"📢 *COMUNICADO OFICIAL:*\n\n{msg_text}", parse_mode=ParseMode.MARKDOWN)
            success_count += 1
            await asyncio.sleep(0.05)  # Respeita o rate limit do Telegram
        except Exception:
            fail_count += 1

    report = f"✅ *Transmissão Finalizada!*\n\n• Sucessos: `{success_count}`\n• Falhas/Bloqueios: `{fail_count}`"
    await update.message.reply_text(report, parse_mode=ParseMode.MARKDOWN)

async def cmd_promover(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id): return

    if len(context.args) < 2:
        await update.message.reply_text("ℹ️ *Uso:* `/promover <USER_ID> <free|pro|unlimited>`", parse_mode=ParseMode.MARKDOWN)
        return

    target_id = int(context.args[0])
    target_tier = context.args[1].lower()

    if target_tier not in ("free", "pro", "unlimited"):
        await update.message.reply_text("❌ Tier inválido. Use `free`, `pro` ou `unlimited`.")
        return

    await db.set_user_tier(target_id, target_tier)
    await update.message.reply_text(f"✅ Usuário `{target_id}` promovido para o plano *{target_tier.upper()}*!", parse_mode=ParseMode.MARKDOWN)

async def cmd_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id): return
    if not context.args:
        await update.message.reply_text("ℹ️ *Uso:* `/ban <USER_ID>`")
        return
    target_id = int(context.args[0])
    await db.set_user_status(target_id, "banned")
    await update.message.reply_text(f"🚫 Usuário `{target_id}` foi banido do sistema.")

async def cmd_unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id): return
    if not context.args:
        await update.message.reply_text("ℹ️ *Uso:* `/unban <USER_ID>`")
        return
    target_id = int(context.args[0])
    await db.set_user_status(target_id, "active")
    await update.message.reply_text(f"✅ Usuário `{target_id}` foi reativado no sistema.")

def register_admin(app: Application):
    app.add_handler(CommandHandler("admin", cmd_admin))
    app.add_handler(CommandHandler("broadcast", cmd_broadcast))
    app.add_handler(CommandHandler("promover", cmd_promover))
    app.add_handler(CommandHandler("ban", cmd_ban))
    app.add_handler(CommandHandler("unban", cmd_unban))
    app.add_handler(CallbackQueryHandler(callback_admin_actions, pattern="^admin:"))
