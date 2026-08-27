"""
Telegram Inline Button Callback Query Handlers — Modern Executive Design System.
"""
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CallbackQueryHandler, ContextTypes
from app.database import db
from app.core import llm_router

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

    # --- 2. Roteamento do Menu Principal ---
    elif data == "menu:main":
        from app.handlers.commands import cmd_menu
        await cmd_menu(update, context)

    elif data == "menu:modelos":
        from app.handlers.commands import cmd_modelos
        await cmd_modelos(update, context)

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

    elif data == "menu:prompt_help":
        text = (
            "🎭 *PERSONALIZAÇÃO DA PERSONA DA IA*\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "Defina instruções personalizadas para o estilo de resposta do assistente.\n\n"
            "📌 *Exemplos de Comandos:*\n"
            "• `/prompt Você é um desenvolvedor sênior em Python e arquiteto de software, direto e técnico.`\n"
            "• `/prompt Você é um consultor financeiro especialista em investimentos.`\n"
            "• `/prompt` (envie sem texto para restaurar a persona padrão)."
        )
        back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="menu:main")]])
        await query.edit_message_text(text, reply_markup=back_kb, parse_mode=ParseMode.MARKDOWN)

    elif data == "menu:ajuda":
        text = (
            "📖 *GUIA DE RECURSOS DO BRAINBOT*\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "• `/menu` — Abre o Menu Principal Interativo\n"
            "• `/modelos` — Alterne entre DeepSeek V4, R1, Gemini, Groq e GPT-4o\n"
            "• `/limpar` — Inicia um Novo Chat limpo\n"
            "• `/web <busca>` — Pesquisa na internet com síntese em tempo real\n"
            "• `/imagem <prompt>` — Gera ilustrações com o Flux.1\n"
            "• `/status` — Exibe dados da sessão e telemetria\n"
            "• `/prompt <texto>` — Ajusta a persona do assistente\n"
            "• `/admin` — Painel Master (Telemetria, Backup SQLite e Broadcast)\n\n"
            "💡 *Capacidades Multimodais Nativas:*\n"
            "Envie **Áudios de voz** (transcrição Whisper instantânea), **Fotos** (leitura OCR/Visão) ou **PDFs/Documentos** diretamente no chat."
        )
        back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="menu:main")]])
        await query.edit_message_text(text, reply_markup=back_kb, parse_mode=ParseMode.MARKDOWN)

def register_callbacks(app: Application):
    app.add_handler(CallbackQueryHandler(callback_router, pattern="^(set_model:|menu:)"))
