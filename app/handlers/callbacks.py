"""
Telegram Inline Button Callback Query Handlers with Complete Menu Routing.
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
            f"✅ **Modelo Ativado com Sucesso!**\n\n"
            f"🤖 **Nome:** {model_info['name']}\n"
            f"🏢 **Provedor:** {model_info['provider']}\n"
            f"📝 **Detalhes:** _{model_info['description']}_"
        )
        back_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Trocar Outro Modelo", callback_data="menu:modelos")],
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
            "🌐 **PESQUISA NA WEB AO VIVO**\n\n"
            "O BrainBot é conectado diretamente à internet via DuckDuckGo.\n\n"
            "📌 **Como Usar:**\n"
            "Digite no chat:\n"
            "`/web últimas notícias sobre inteligência artificial`\n\n"
            "O bot fará a busca em tempo real, sintetizará os dados mais recentes e responderá com referências."
        )
        back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="menu:main")]])
        await query.edit_message_text(text, reply_markup=back_kb, parse_mode=ParseMode.MARKDOWN)

    elif data == "menu:img_help":
        text = (
            "🎨 **GERAÇÃO DE IMAGENS EM ALTA DEFINIÇÃO**\n\n"
            "O bot utiliza o modelo de última geração **Flux.1**.\n\n"
            "📌 **Como Usar:**\n"
            "Digite no chat:\n"
            "`/imagem um astronauta explorando uma floresta alienígena em neon 8k`\n\n"
            "A imagem será renderizada e enviada em alta resolução diretamente na conversa."
        )
        back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="menu:main")]])
        await query.edit_message_text(text, reply_markup=back_kb, parse_mode=ParseMode.MARKDOWN)

    elif data == "menu:prompt_help":
        text = (
            "🎭 **PERSONALIZAÇÃO DA PERSONA DA IA**\n\n"
            "Você pode definir uma instrução personalizada para o assistente responder no estilo que você preferir.\n\n"
            "📌 **Exemplos de Uso:**\n"
            "• `/prompt Você é um programador sênior em Python e Rust, direto e técnico.`\n"
            "• `/prompt Você é um consultor de negócios especialista em finanças.`\n"
            "• `/prompt` (sem argumentos para voltar ao padrão)."
        )
        back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="menu:main")]])
        await query.edit_message_text(text, reply_markup=back_kb, parse_mode=ParseMode.MARKDOWN)

    elif data == "menu:ajuda":
        text = (
            "📖 **GUIA COMPLETO DE COMANDOS DO BRAINBOT**\n\n"
            "• `/menu` - Abre o Menu Interativo Principal\n"
            "• `/modelos` - Alterne entre DeepSeek V4, R1, Gemini, Groq e GPT-4o\n"
            "• `/limpar` - Inicia um Novo Chat (limpa a memória recente)\n"
            "• `/web <busca>` - Pesquisa notícias e fatos na internet ao vivo\n"
            "• `/imagem <prompt>` - Cria imagens realistas com o Flux.1\n"
            "• `/status` - Mostra modelo ativo e dados da sessão\n"
            "• `/prompt <texto>` - Customiza a personalidade da IA\n"
            "• `/admin` - Painel Master (Telemetria, Backup SQLite e Broadcast)\n\n"
            "💡 **Dica Multimodal:** Envie fotos (para OCR/visão), áudios de voz (transcritos via Whisper) ou PDFs diretamente no chat."
        )
        back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="menu:main")]])
        await query.edit_message_text(text, reply_markup=back_kb, parse_mode=ParseMode.MARKDOWN)

def register_callbacks(app: Application):
    app.add_handler(CallbackQueryHandler(callback_router, pattern="^(set_model:|menu:)"))
