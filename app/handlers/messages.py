"""
Master Message Handler: Real-Time Streaming, Client Quotas, Long-Term Memory, Real-Time Web Grounding, and TTS Voice Synthesis.
"""
import asyncio
import logging
import time
from telegram import Update
from telegram.constants import ParseMode, ChatAction
from telegram.error import BadRequest
from telegram.ext import Application, MessageHandler, ContextTypes, filters
from app.config import settings
from app.database import db
from app.core import (
    llm_router,
    web_search_engine,
    url_reader,
    chart_generator,
    tts_engine
)
from app.handlers.commands import show_unauthorized_card

logger = logging.getLogger(__name__)

async def keep_typing_alive(bot, chat_id: int, stop_event: asyncio.Event):
    """Mantém a indicação de 'digitando...' ativa no topo do chat do Telegram."""
    try:
        while not stop_event.is_set():
            await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            await asyncio.sleep(4)
    except Exception:
        pass

async def stream_chat_response(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_prompt: str,
    user_id: int,
    is_voice_input: bool = False
):
    """Executa a resposta completa com inteligência multi-camadas e cotas diárias de clientes."""
    
    # 0. Verificação de Autorização e Cotas de Uso
    if not await db.is_user_authorized(user_id):
        await show_unauthorized_card(update, context)
        return

    allowed, current_count, max_quota, tier = await db.check_and_increment_quota(user_id)
    if not allowed:
        quota_text = (
            f"⚠️ *LIMITE DIÁRIO ATINGIDO*\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"Você atingiu o limite de **{max_quota} mensagens diárias** do plano *{tier.upper()}*.\n\n"
            f"• Sua cota será renovada automaticamente amanhã às 00:00.\n"
            f"• Para migrar para o plano Pro ou VIP Ilimitado, converse com `{settings.ADMIN_CONTACT}`."
        )
        await update.message.reply_text(quota_text, parse_mode=ParseMode.MARKDOWN)
        return

    user = await db.get_or_create_user(user_id)
    history = await db.get_context_history(user_id)
    selected_model = user["selected_model"]
    custom_sys = user.get("custom_system_prompt")
    chat_id = update.effective_chat.id

    # 1. Recupera Memórias Permanentes de Longo Prazo do Usuário
    memories = await db.get_memories(user_id)
    memory_context = ""
    if memories:
        memory_lines = [f"- {m['memory_text']}" for m in memories]
        memory_context = "\n\n[MEMÓRIAS PERMANENTES E PREFERÊNCIAS SALVAS DO USUÁRIO]:\n" + "\n".join(memory_lines)

    base_system_prompt = custom_sys or ""
    full_system_prompt = base_system_prompt + memory_context if (base_system_prompt or memory_context) else None

    stop_typing_event = asyncio.Event()
    typing_task = asyncio.create_task(keep_typing_alive(context.bot, chat_id, stop_typing_event))

    msg_status = await update.message.reply_text("✨ *Processando...*", parse_mode=ParseMode.MARKDOWN)

    # 2. Detecção e Leitura Automática de Links / URLs
    final_prompt = user_prompt
    urls = url_reader.extract_urls(user_prompt)
    if urls:
        try:
            target_url = urls[0]
            await msg_status.edit_text(f"🔗 *Acessando conteúdo da página:* `{target_url}`...", parse_mode=ParseMode.MARKDOWN)
            page_text = await url_reader.fetch_page_content(target_url)
            await db.record_usage(user_id, "url_read")
            final_prompt = (
                f"[CONTEÚDO DA PÁGINA WEB EXTRAÍDO]:\n{page_text}\n\n"
                f"[SOLICITAÇÃO DO USUÁRIO]:\n{user_prompt}\n\n"
                "Instrução: Analise as informações da página web extraída acima e elabore uma resposta estruturada."
            )
        except Exception as e:
            logger.warning(f"Falha na leitura da URL: {e}")

    # 3. Detecção Inteligente de Busca na Web (Auto Web Grounding)
    elif web_search_engine.should_trigger_search(user_prompt):
        try:
            await msg_status.edit_text("🌐 *Consultando a internet em tempo real...*", parse_mode=ParseMode.MARKDOWN)
            web_data = await web_search_engine.search(user_prompt, max_results=5)
            await db.record_usage(user_id, "web_search")
            final_prompt = (
                f"{web_data}\n\n"
                f"[PERGUNTA DO USUÁRIO]:\n{user_prompt}\n\n"
                "Instrução: Use os dados mais recentes da web fornecidos acima para responder à pergunta do usuário com precisão, clareza e autoridade. "
                "Cite as fontes e nunca diga que não tem acesso à internet."
            )
        except Exception as e:
            logger.warning(f"Falha na auto-busca web: {e}")

    # 4. Detecção de Gráficos (Data Analysis)
    is_chart_req = chart_generator.is_chart_request(user_prompt)
    if is_chart_req:
        final_prompt += (
            "\n\n[INSTRUÇÃO IMPORTANTE]: Como o usuário solicitou um gráfico, inclua no final da sua resposta "
            "um bloco de código Python executável usando exclusivamente a biblioteca `matplotlib.pyplot` (como `plt`), "
            "sem placeholders, sem plt.show(), apenas com os dados e customização visual pronta."
        )

    messages = history + [{"role": "user", "content": final_prompt}]
    
    last_update = time.time()
    accumulated_text = ""
    accumulated_reasoning = ""
    actual_model_used = selected_model
    fallback_alert = ""

    try:
        async for text_chunk, reasoning_chunk, current_model, fb_notice in llm_router.stream_response(
            model_key=selected_model,
            messages=messages,
            system_prompt=full_system_prompt
        ):
            accumulated_text = text_chunk
            actual_model_used = current_model
            if fb_notice:
                fallback_alert = fb_notice
            if reasoning_chunk:
                accumulated_reasoning = reasoning_chunk

            now = time.time()
            if now - last_update >= settings.STREAMING_THROTTLE_SECONDS and accumulated_text.strip():
                display = accumulated_text
                if accumulated_reasoning:
                    display = f"💭 _Raciocínio:_\n`{accumulated_reasoning[-200:]}`\n\n{accumulated_text}"
                
                if len(display) > 4000:
                    display = display[:3990] + "..."

                try:
                    await msg_status.edit_text(display, parse_mode=ParseMode.MARKDOWN)
                    last_update = now
                except BadRequest:
                    pass
                except Exception:
                    pass

        stop_typing_event.set()
        await typing_task

        if accumulated_text.strip():
            await db.save_message(user_id, "user", user_prompt, actual_model_used)
            await db.save_message(user_id, "assistant", accumulated_text, actual_model_used)
            await db.record_usage(user_id, "text", actual_model_used)

            model_badge = llm_router.AVAILABLE_MODELS.get(actual_model_used, {}).get("badge", actual_model_used)
            footer = f"\n\n▫️ _{model_badge}_"
            if fallback_alert:
                footer = f"\n\n{fallback_alert}\n▫️ _{model_badge}_"

            final_text = accumulated_text.strip() + footer

            if len(final_text) <= 4090:
                try:
                    await msg_status.edit_text(final_text, parse_mode=ParseMode.MARKDOWN)
                except Exception:
                    await msg_status.edit_text(final_text)
            else:
                try:
                    await msg_status.edit_text(final_text[:4000], parse_mode=ParseMode.MARKDOWN)
                except Exception:
                    await msg_status.edit_text(final_text[:4000])
                
                for i in range(4000, len(final_text), 4000):
                    chunk = final_text[i:i+4000]
                    try:
                        await update.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN)
                    except Exception:
                        await update.message.reply_text(chunk)

            # 5. Execução e Envio de Gráficos (se solicitado)
            if is_chart_req and "plt." in accumulated_text:
                try:
                    chart_buf = chart_generator.extract_and_run_matplotlib(accumulated_text)
                    if chart_buf:
                        await update.message.reply_photo(
                            photo=chart_buf,
                            caption="📊 *Gráfico gerado com sucesso pelo BrainBot Data Engine*",
                            parse_mode=ParseMode.MARKDOWN
                        )
                except Exception as chart_err:
                    logger.warning(f"Falha ao gerar gráfico: {chart_err}")

            # 6. Resposta Falada por Áudio (Text-to-Speech)
            voice_enabled = await db.is_voice_mode_enabled(user_id)
            if is_voice_input or voice_enabled:
                try:
                    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.RECORD_VOICE)
                    voice_buffer = await tts_engine.generate_voice_bytes(accumulated_text)
                    if voice_buffer:
                        await update.message.reply_voice(
                            voice=voice_buffer,
                            caption="🎙️ *BrainBot Voice Response*"
                        )
                except Exception as tts_err:
                    logger.warning(f"Falha no envio de voz TTS: {tts_err}")

    except Exception as e:
        stop_typing_event.set()
        logger.error(f"Erro no processamento de mensagem: {e}")
        try:
            await msg_status.edit_text(f"❌ Ocorreu um erro ao processar sua resposta: `{e}`", parse_mode=ParseMode.MARKDOWN)
        except Exception:
            pass

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await db.is_user_authorized(user_id):
        await show_unauthorized_card(update, context)
        return
    
    text = update.message.text
    if not text: return
    
    await stream_chat_response(update, context, text, user_id)

def register_messages(app: Application):
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
