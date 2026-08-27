"""
Telegram Inline Button Callback Query Handlers with Complete Superpower Routing.
"""
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode, ChatAction
from telegram.ext import Application, CallbackQueryHandler, ContextTypes
from app.database import db
from app.core import (
    llm_router,
    conversation_exporter,
    SPECIALIZED_ASSISTANTS
)

logger = logging.getLogger(__name__)

async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    data = query.data

    # --- 1. Troca de Modelo de IA ---
    if data.startswith("set_model:"):
        model_key = data.split(":", 1)[1]
        model_info = llm_router.AVAILABLE_MODELS.get(model_key)
        
        if not model_info:
            await query.edit_message_text("❌ Modelo não reconhecido.")
            return

        await db.update_user_model(user_id, model_key)
        
        confirmation = (
            "✅ *MOTOR DE IA ATIVADO COM SUCESSO!*\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            f"🤖 *Nome:* {model_info['name']}\n"
            f"🏢 *Provedor:* `{model_info['provider']}`\n"
            f"📝 *Foco:* _{model_info['description']}_"
        )
        back_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Escolher Outro Modelo", callback_data="menu:modelos")],
            [InlineKeyboardButton("⬅️ Voltar ao Menu Principal", callback_data="menu:main")]
        ])
        await query.edit_message_text(confirmation, reply_markup=back_kb, parse_mode=ParseMode.MARKDOWN)

    # --- 2. Seleção de Assistentes Especialistas (GPTs) ---
    elif data.startswith("set_asst:"):
        asst_key = data.split(":", 1)[1]
        if asst_key == "default":
            await db.update_user_system_prompt(user_id, None)
            text = "🔄 *Assistente Padrão Restaurado!*"
        else:
            asst = SPECIALIZED_ASSISTANTS.get(asst_key)
            if asst:
                await db.update_user_system_prompt(user_id, asst["system_prompt"])
                text = (
                    f"🎭 *PERFIL ATIVADO:* {asst['name']}\n"
                    "━━━━━━━━━━━━━━━━━━━━━\n"
                    f"📝 *Especialidade:* _{asst['description']}_\n\n"
                    "O BrainBot agora responderá com esta persona especializada."
                )
            else:
                text = "❌ Especialista não encontrado."

        back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="menu:main")]])
        await query.edit_message_text(text, reply_markup=back_kb, parse_mode=ParseMode.MARKDOWN)

    # --- 3. Exportação de Histórico ---
    elif data.startswith("export:"):
        fmt = data.split(":", 1)[1]
        history = await db.get_full_conversation_history(user_id)
        if not history:
            await query.edit_message_text("ℹ️ *Não há histórico de conversas para exportar.*", parse_mode=ParseMode.MARKDOWN)
            return

        user_name = update.effective_user.first_name or "Usuário"
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_DOCUMENT)
        
        if fmt == "pdf":
            file_buf = conversation_exporter.export_to_pdf(history, user_name)
            caption = "📄 *Seu relatório completo de conversa em PDF.*"
        elif fmt == "md":
            file_buf = conversation_exporter.export_to_markdown(history, user_name)
            caption = "📝 *Seu histórico de conversa em Markdown formatado.*"
        else:
            file_buf = conversation_exporter.export_to_txt(history, user_name)
            caption = "📋 *Seu histórico de conversa em TXT.*"

        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=file_buf,
            filename=file_buf.name,
            caption=caption,
            parse_mode=ParseMode.MARKDOWN
        )

    # --- 4. Gerenciamento de Memórias ---
    elif data == "memories:clear_all":
        await db.clear_memories(user_id)
        back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="menu:main")]])
        await query.edit_message_text("🗑️ *Todas as memórias de longo prazo foram apagadas.*", reply_markup=back_kb, parse_mode=ParseMode.MARKDOWN)

    # --- 5. Roteamento de Menus ---
    elif data == "menu:main":
        from app.handlers.commands import cmd_menu
        await cmd_menu(update, context)

    elif data == "menu:modelos":
        from app.handlers.commands import cmd_modelos
        await cmd_modelos(update, context)

    elif data == "menu:assistentes":
        from app.handlers.commands import cmd_assistentes
        await cmd_assistentes(update, context)

    elif data == "menu:toggle_voice":
        from app.handlers.commands import cmd_voz
        await cmd_voz(update, context)

    elif data == "menu:memorias":
        from app.handlers.commands import cmd_memorias
        await cmd_memorias(update, context)

    elif data == "menu:exportar":
        from app.handlers.commands import cmd_exportar
        await cmd_exportar(update, context)

    elif data == "menu:limpar":
        from app.handlers.commands import cmd_limpar
        await cmd_limpar(update, context)

    elif data == "menu:status":
        from app.handlers.commands import cmd_status
        await cmd_status(update, context)

    elif data == "menu:web_help":
        text = (
            "🌐 *PESQUISA NA WEB INTELIGENTE (AUTOMÁTICA)*\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "O BrainBot pesquisa a internet **automaticamente** sempre que você fizer perguntas sobre:\n"
            "• Notícias recentes e acontecimentos de hoje\n"
            "• Clima, temperatura e previsões\n"
            "• Cotações (Dólar, Bitcoin, Ações)\n"
            "• Lançamentos e atualizações\n\n"
            "💡 *Você também pode forçar a busca digitando:*\n"
            "`/web notícias de inteligência artificial`"
        )
        back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="menu:main")]])
        await query.edit_message_text(text, reply_markup=back_kb, parse_mode=ParseMode.MARKDOWN)

    elif data == "menu:img_help":
        text = (
            "🎨 *GERAÇÃO DE IMAGENS EM ALTA DEFINIÇÃO*\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "Renderização de última geração alimentada pelo modelo **Flux.1**.\n\n"
            "📌 *Como Utilizar:*\n"
            "Digite no chat a qualquer momento:\n"
            "`/imagem um astronauta explorando uma floresta alienígena 8k`\n\n"
            "A imagem será renderizada em 1024x1024 e enviada direto no chat."
        )
        back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="menu:main")]])
        await query.edit_message_text(text, reply_markup=back_kb, parse_mode=ParseMode.MARKDOWN)

    elif data == "menu:ajuda":
        text = (
            "📖 *GUIA COMPLETO DE RECURSOS DO BRAINBOT*\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "• `/menu` — Abre o Menu Principal Interativo\n"
            "• `/modelos` — Alterne entre DeepSeek V4, R1, Gemini, Groq e GPT-4o\n"
            "• `/assistentes` — Escolha personas profissionais (Dev, Finanças, Copywriter, etc)\n"
            "• `/voz` — Liga/desliga o modo de respostas faladas em áudio\n"
            "• `/lembrar <fato>` — Grava memórias permanentes sobre você\n"
            "• `/memorias` — Lista e gerencia suas memórias salvas\n"
            "• `/exportar` — Baixa o histórico da conversa em PDF, Markdown ou TXT\n"
            "• `/limpar` — Inicia um Novo Chat limpo\n"
            "• `/web <busca>` — Pesquisa na internet com síntese em tempo real\n"
            "• `/imagem <prompt>` — Gera ilustrações em alta definição (Flux.1)\n"
            "• `/status` — Exibe dados da sessão e telemetria do servidor\n"
            "• `/admin` — Painel Master Admin (Telemetria, Backup SQLite e Broadcast)\n\n"
            "💡 *Superpoderes Automáticos Nativos:*\n"
            "• **Links Web:** Cole qualquer link (`http...`) para o bot ler e resumir o site.\n"
            "• **Gráficos:** Peça *\"crie um gráfico de barras...\"* e receba a imagem renderizada.\n"
            "• **Multimodal:** Envie Fotos, PDFs ou Áudios de voz a qualquer momento."
        )
        back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="menu:main")]])
        await query.edit_message_text(text, reply_markup=back_kb, parse_mode=ParseMode.MARKDOWN)

def register_callbacks(app: Application):
    app.add_handler(CallbackQueryHandler(callback_router, pattern="^(set_model:|set_asst:|export:|memories:|menu:)"))
