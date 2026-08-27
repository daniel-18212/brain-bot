"""
Institutional Admin Control Panel & Master Client Management Center for Telegram.
"""
import asyncio
from datetime import datetime
import io
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode, ChatAction
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from app.config import settings
from app.database import db
from app.core.resilience import telemetry

logger = logging.getLogger(__name__)

def is_admin(user_id: int) -> bool:
    return user_id == settings.ADMIN_USER_ID

MARKETING_COPY = (
    "🚀 *BRAINBOT AI — TODAS AS MELHORES INTELIGÊNCIAS ARTIFICIAIS EM 1 SÓ LUGAR!*\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    "Pare de pagar várias assinaturas caras todo mês. Veja quanto custa assinar cada IA separadamente:\n\n"
    "| Plataforma | Plano Individual | Preço Oficial |\n"
    "| :--- | :--- | :--- |\n"
    "| **ChatGPT** | Plus Oficial | **R$ 99,90/mês** |\n"
    "| **Grok** | SuperGrok | **R$ 149,90/mês** |\n"
    "| **Google Gemini** | Google AI Pro | **R$ 96,99/mês** |\n"
    "| **GitHub Copilot** | Pro+ | **US$ 39 (~R$ 220,00)** |\n\n"
    "💸 *Total somado:* **Mais de R$ 560,00 por mês!**\n\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    "⭐ *COM O BRAINBOT VOCÊ TEM TUDO POR APENAS:*\n"
    "🔥 **R$ 30,00 / mês** *(Menos de R$ 1,00 por dia!)*\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    "🧠 *O que está incluso no seu acesso:*\n"
    "• ⚡ **Top 4 IAs do Mundo:** DeepSeek V4 (Código), DeepSeek R1 (Raciocínio), Gemini 3.6 Flash e GPT-OSS 120B.\n"
    "• 🎙️ **Áudio e Voz Humana:** Mande áudio e o bot transcreve e responde falando em português brasileiro natural.\n"
    "• 📄 **Leitor Completo de PDFs e Documentos:** Envie contratos, planilhas e relatórios para análise.\n"
    "• 🖼️ **Visão Computacional:** Identifica fotos, gráficos, prints e recibos.\n"
    "• 🌐 **Busca Web em Tempo Real:** Responde notícias de hoje, cotações e clima.\n"
    "• 📊 **Data Analysis:** Gera e envia gráficos prontos em alta definição.\n"
    "• 📑 **Exportação de Relatórios:** Baixe suas conversas e estudos em PDF formatado.\n"
    "• 🎭 **Especialistas Prontos:** Modos Dev Sênior, Analista Financeiro, Copywriter e Professor de Inglês.\n\n"
    "🔒 *Sem pegadinhas, sem limites ocultos, direto no seu Telegram sem precisar instalar nada.*\n\n"
    f"👉 **Adquira seu acesso agora chamando:** {settings.ADMIN_CONTACT}"
)

async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Painel Principal de Administração Master."""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ Acesso Restrito: Apenas o Master Admin pode acessar este menu.")
        return

    keyboard = [
        [
            InlineKeyboardButton("👥 Gestão de Clientes & Planos", callback_data="admin:clients"),
            InlineKeyboardButton("📈 Métricas & Telemetria", callback_data="admin:metrics"),
        ],
        [
            InlineKeyboardButton("📢 Gerar Copy de Marketing (Vendas)", callback_data="admin:marketing"),
            InlineKeyboardButton("📣 Disparo Global (Broadcast)", callback_data="admin:broadcast_help"),
        ],
        [
            InlineKeyboardButton("💾 Backup do Banco (.sqlite)", callback_data="admin:backup"),
            InlineKeyboardButton("🔒 Alternar Modo de Acesso", callback_data="admin:access_mode"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    admin_dashboard_text = (
        "🎛️ *PAINEL MASTER ADMIN — BRAINBOT ENTERPRISE*\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"👑 *Master Admin:* `{settings.ADMIN_USER_ID}`\n"
        f"🔒 *Modo de Acesso:* `{settings.ACCESS_MODE}`\n"
        f"🩺 *Health Server:* `Online (Porta {settings.HEALTH_PORT})`\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "Selecione uma área de controle para gerenciar seus clientes ou a infraestrutura do bot:"
    )
    if update.callback_query:
        await update.callback_query.edit_message_text(admin_dashboard_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(admin_dashboard_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

async def cmd_marketing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gera o texto de marketing pronto para divulgação."""
    user_id = update.effective_user.id
    if not is_admin(user_id): return
    await update.message.reply_text(MARKETING_COPY, parse_mode=ParseMode.MARKDOWN)

async def callback_admin_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    if not is_admin(user_id): return

    action = query.data

    # --- 1. Gestão de Clientes ---
    if action == "admin:clients":
        top = await db.get_top_users(limit=10)
        lines = [
            "👥 *GESTÃO DE CLIENTES & PLANOS ATIVOS*",
            "━━━━━━━━━━━━━━━━━━━━━"
        ]
        for idx, u in enumerate(top, start=1):
            uname = f"@{u["username"]}" if u["username"] else u["first_name"] or "Sem Nome"
            status_icon = "🟢" if u["status"] == "active" else ("⏳" if u["status"] == "pending" else "🔴")
            lines.append(f"{idx}. {status_icon} *{uname}* (ID: `{u["user_id"]}`)\n   ⭐ Plano: `{u["tier"].upper()}` | 💬 Msgs: `{u["message_count"]}`")

        lines.append(
            "\n━━━━━━━━━━━━━━━━━━━━━\n"
            "💡 *Ações Rápidas via Comando:*\n"
            "• `/promover <ID> <free|pro|unlimited>`\n"
            "• `/ban <ID>` — Bloqueia cliente\n"
            "• `/unban <ID>` — Reativa cliente\n"
            "• `/role <ID> <admin|user>` — Altera papel"
        )
        back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar ao Painel", callback_data="admin:main")]])
        await query.edit_message_text("\n".join(lines), reply_markup=back_kb, parse_mode=ParseMode.MARKDOWN)

    # --- 2. Copy de Marketing ---
    elif action == "admin:marketing":
        back_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Voltar ao Painel", callback_data="admin:main")]
        ])
        await query.edit_message_text(MARKETING_COPY, reply_markup=back_kb, parse_mode=ParseMode.MARKDOWN)

    # --- 3. Métricas de Negócio & Servidor ---
    elif action == "admin:metrics":
        stats = await db.get_admin_dashboard_stats()
        m = telemetry.get_metrics()
        text = (
            "📈 *PAINEL EXECUTIVO DE MÉTRICAS & NEGÓCIO*\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            f"👥 *Total de Clientes:* `{stats["total_users"]}` (🟢 Ativos: `{stats["active_users"]}` | ⏳ Pendentes: `{stats["pending_users"]}`)\n"
            f"⭐ *Assinantes Pro / VIP:* `{stats["pro_users"]}`\n"
            f"💬 *Mensagens Processadas:* `{stats["total_messages"]}` (Hoje: `{stats["messages_today"]}`)\n"
            f"🎨 *Imagens Geradas:* `{stats["images_gen"]}` | 🌐 *Buscas Web:* `{stats["web_searches"]}`\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚡ *CPU:* `{m["cpu_percent"]}%` | 🧠 *RAM:* `{m["ram_used_mb"]:.1f} MB` ({m["ram_percent"]}%)\n"
            f"💽 *Disco:* `{m["disk_used_gb"]:.1f} GB` | 🗄️ *Banco SQLite:* `{m["db_size_mb"]} MB`\n"
            f"⏱️ *Uptime do Servidor:* `{m["uptime"]}`"
        )
        back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar ao Painel", callback_data="admin:main")]])
        await query.edit_message_text(text, reply_markup=back_kb, parse_mode=ParseMode.MARKDOWN)

    # --- 4. Ajuda de Broadcast ---
    elif action == "admin:broadcast_help":
        text = (
            "📣 *TRANSMISSÃO EM MASSA (BROADCAST)*\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "Envie comunicados para todos os clientes ativos de uma vez.\n\n"
            "📌 *Como Utilizar:*\n"
            "`/broadcast Olá a todos! Adicionamos novos recursos ao BrainBot...`\n\n"
            "O bot enviará a mensagem individualmente respeitando o rate limit do Telegram."
        )
        back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar ao Painel", callback_data="admin:main")]])
        await query.edit_message_text(text, reply_markup=back_kb, parse_mode=ParseMode.MARKDOWN)

    # --- 5. Alternar Modo de Acesso ---
    elif action == "admin:access_mode":
        current = settings.ACCESS_MODE
        modes = ["WHITELIST", "PRIVATE", "PUBLIC"]
        next_mode = modes[(modes.index(current) + 1) % len(modes)]
        settings.ACCESS_MODE = next_mode
        await db.set_system_setting("ACCESS_MODE", next_mode)
        
        text = (
            "🔒 *MODO DE ACESSO ALTERADO!*\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            f"Novo modo ativo: `{next_mode}`\n\n"
            "• **WHITELIST:** Novos clientes solicitam autorização com 1 clique.\n"
            "• **PRIVATE:** Apenas você (Admin) pode utilizar.\n"
            "• **PUBLIC:** Aberto a qualquer usuário."
        )
        back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar ao Painel", callback_data="admin:main")]])
        await query.edit_message_text(text, reply_markup=back_kb, parse_mode=ParseMode.MARKDOWN)

    # --- 6. Backup do Banco SQLite ---
    elif action == "admin:backup":
        await query.edit_message_text("💾 *Gerando cópia de segurança do banco de dados...*", parse_mode=ParseMode.MARKDOWN)
        if settings.DATABASE_PATH.exists():
            with open(settings.DATABASE_PATH, "rb") as f:
                now_s = datetime.now().strftime("%Y%m%d_%H%M%S")
                await context.bot.send_document(
                    chat_id=user_id,
                    document=f,
                    filename=f"backup_brainbot_{now_s}.sqlite",
                    caption="💾 *Backup do Banco de Dados SQLite Concluído!*"
                )
        else:
            await query.edit_message_text("❌ Arquivo de banco de dados não encontrado.")

    # --- 7. Voltar ao Painel Admin ---
    elif action == "admin:main":
        await cmd_admin(update, context)

# --- Comandos Administrativos Adicionais ---

async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id): return

    msg_text = " ".join(context.args)
    if not msg_text:
        await update.message.reply_text("ℹ️ *Uso:* `/broadcast Olá a todos! Nova funcionalidade adicionada...`", parse_mode=ParseMode.MARKDOWN)
        return

    users = await db.get_all_users_for_broadcast()
    await update.message.reply_text(f"📢 *Iniciando transmissão para {len(users)} clientes...*", parse_mode=ParseMode.MARKDOWN)

    success_count = 0
    fail_count = 0

    for uid in users:
        try:
            bcast_msg = f"📢 *COMUNICADO DO ADMINISTRADOR:*\n\n{msg_text}"
            await context.bot.send_message(chat_id=uid, text=bcast_msg, parse_mode=ParseMode.MARKDOWN)
            success_count += 1
            await asyncio.sleep(0.05)
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

async def cmd_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Altera o papel de um usuário para admin ou user."""
    user_id = update.effective_user.id
    if not is_admin(user_id): return

    if len(context.args) < 2:
        await update.message.reply_text("ℹ️ *Uso:* `/role <USER_ID> <admin|user>`", parse_mode=ParseMode.MARKDOWN)
        return

    target_id = int(context.args[0])
    target_role = context.args[1].lower()

    if target_role not in ("admin", "user"):
        await update.message.reply_text("❌ Papel inválido. Use `admin` ou `user`.")
        return

    async with db.get_connection() as conn:
        await conn.execute("UPDATE users SET role = ? WHERE user_id = ?", (target_role, target_id))
        await conn.commit()

    await update.message.reply_text(f"✅ Papel do usuário `{target_id}` alterado para *{target_role.upper()}*!", parse_mode=ParseMode.MARKDOWN)

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
    app.add_handler(CommandHandler("marketing", cmd_marketing))
    app.add_handler(CommandHandler("broadcast", cmd_broadcast))
    app.add_handler(CommandHandler("promover", cmd_promover))
    app.add_handler(CommandHandler("role", cmd_role))
    app.add_handler(CommandHandler("ban", cmd_ban))
    app.add_handler(CommandHandler("unban", cmd_unban))
    app.add_handler(CallbackQueryHandler(callback_admin_actions, pattern="^admin:"))
