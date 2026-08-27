"""
Unified Multi-Provider LLM Router with Streaming, Fallback Chains, and Free-Tier Maximization.
"""
from typing import AsyncGenerator
import logging
from openai import AsyncOpenAI
import google.generativeai as genai
from app.config import settings

logger = logging.getLogger(__name__)

# Configuração global do Google Gemini se a chave estiver presente
if settings.GEMINI_API_KEY:
    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
    except Exception as e:
        logger.warning(f"Aviso ao inicializar Gemini: {e}")

class LLMRouter:
    DEFAULT_SYSTEM_PROMPT = """Você é o BrainBot, um assistente de inteligência artificial de elite, versátil, ultra-rápido, perspicaz e prestativo.
- Responda em português fluente (a menos que o usuário solicite outro idioma).
- Use formatação Markdown elegante e limpa: títulos, negrito, listas e blocos de código com a linguagem especificada.
- Se for solicitado código, forneça soluções prontas para produção, bem comentadas e sem placeholders desnecessários."""

    AVAILABLE_MODELS = {
        "gemini": {
            "name": "⚡ Gemini 2.0 Flash",
            "provider": "Google (Grátis)",
            "description": "Ultra rápido, multimodal e com contexto massivo."
        },
        "gemini-pro": {
            "name": "🌟 Gemini 1.5 Pro",
            "provider": "Google (Grátis)",
            "description": "Raciocínio aprofundado e análise complexa."
        },
        "groq-llama": {
            "name": "🚀 Llama 3.3 70B",
            "provider": "Groq Cloud (Grátis)",
            "description": "Velocidade extrema (300+ tokens/s) e código."
        },
        "groq-r1": {
            "name": "🧠 DeepSeek R1 (Groq)",
            "provider": "Groq Cloud (Grátis)",
            "description": "Raciocínio profundo destilado gratuito."
        },
        "deepseek": {
            "name": "💡 DeepSeek V3",
            "provider": "DeepSeek API",
            "description": "Excelente para programação e textos longos."
        },
        "deepseek-r1": {
            "name": "🔬 DeepSeek R1 Oficial",
            "provider": "DeepSeek API",
            "description": "Raciocínio encadeado formal passo a passo."
        },
        "openrouter-free": {
            "name": "🌐 OpenRouter Free Router",
            "provider": "OpenRouter (Grátis)",
            "description": "Roteamento inteligente entre modelos abertos gratuitos."
        },
        "openai": {
            "name": "🟢 GPT-4o Mini",
            "provider": "OpenAI",
            "description": "Modelo compacto e rápido da OpenAI."
        }
    }

    def __init__(self):
        # Inicializa clientes assíncronos compatíveis com OpenAI API
        self.client_groq = AsyncOpenAI(
            api_key=settings.GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1"
        ) if settings.GROQ_API_KEY else None

        self.client_deepseek = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com"
        ) if settings.DEEPSEEK_API_KEY else None

        self.client_openrouter = AsyncOpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1"
        ) if settings.OPENROUTER_API_KEY else None

        self.client_openai = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY
        ) if settings.OPENAI_API_KEY else None

    async def stream_response(
        self,
        model_key: str,
        messages: list[dict],
        system_prompt: str | None = None
    ) -> AsyncGenerator[tuple[str, str], None]:
        """
        Executa a geração de resposta via streaming.
        Yields: (texto_acumulado, raciocinio_acumulado)
        """
        sys_prompt = system_prompt or self.DEFAULT_SYSTEM_PROMPT
        
        # Estratégia de Fallback: Se o modelo requisitado falhar, tenta os outros disponíveis
        fallback_order = [model_key, "gemini", "groq-llama", "deepseek", "openrouter-free", "openai"]
        # Remove duplicados mantendo a ordem
        unique_order = list(dict.fromkeys(fallback_order))

        last_error = None
        for current_model in unique_order:
            try:
                # 1. GOOGLE GEMINI
                if current_model in ("gemini", "gemini-pro") and settings.GEMINI_API_KEY:
                    model_target = "gemini-2.0-flash" if current_model == "gemini" else "gemini-1.5-pro"
                    model = genai.GenerativeModel(
                        model_name=model_target,
                        system_instruction=sys_prompt
                    )
                    
                    # Constrói o histórico no formato Gemini
                    history_gemini = []
                    for m in messages[:-1]:
                        role = "user" if m["role"] == "user" else "model"
                        history_gemini.append({"role": role, "parts": [m["content"]]})
                    
                    chat = model.start_chat(history=history_gemini)
                    last_user_msg = messages[-1]["content"] if messages else ""
                    
                    response = await chat.send_message_async(last_user_msg, stream=True)
                    accumulated = ""
                    async for chunk in response:
                        if chunk.text:
                            accumulated += chunk.text
                            yield accumulated, ""
                    return

                # 2. GROQ CLOUD (Llama 3.3 70B & DeepSeek R1 Distill)
                elif current_model in ("groq-llama", "groq-r1") and self.client_groq:
                    groq_model = "llama-3.3-70b-versatile" if current_model == "groq-llama" else "deepseek-r1-distill-llama-70b"
                    formatted_msgs = [{"role": "system", "content": sys_prompt}] + messages
                    
                    stream = await self.client_groq.chat.completions.create(
                        model=groq_model,
                        messages=formatted_msgs,
                        stream=True
                    )
                    
                    accumulated = ""
                    async for chunk in stream:
                        delta = chunk.choices[0].delta
                        if delta.content:
                            accumulated += delta.content
                            yield accumulated, ""
                    return

                # 3. DEEPSEEK (V3 / R1)
                elif current_model in ("deepseek", "deepseek-r1") and self.client_deepseek:
                    ds_model = "deepseek-reasoner" if current_model == "deepseek-r1" else "deepseek-chat"
                    formatted_msgs = [{"role": "system", "content": sys_prompt}] + messages
                    
                    stream = await self.client_deepseek.chat.completions.create(
                        model=ds_model,
                        messages=formatted_msgs,
                        stream=True
                    )
                    
                    accumulated_content = ""
                    accumulated_reasoning = ""
                    async for chunk in stream:
                        delta = chunk.choices[0].delta
                        if hasattr(delta, "reasoning_content") and delta.reasoning_content:
                            accumulated_reasoning += delta.reasoning_content
                        if delta.content:
                            accumulated_content += delta.content
                        yield accumulated_content, accumulated_reasoning
                    return

                # 4. OPENROUTER FREE ROUTER
                elif current_model == "openrouter-free" and self.client_openrouter:
                    formatted_msgs = [{"role": "system", "content": sys_prompt}] + messages
                    stream = await self.client_openrouter.chat.completions.create(
                        model="openrouter/auto",
                        messages=formatted_msgs,
                        stream=True
                    )
                    accumulated = ""
                    async for chunk in stream:
                        delta = chunk.choices[0].delta
                        if delta.content:
                            accumulated += delta.content
                            yield accumulated, ""
                    return

                # 5. OPENAI
                elif current_model == "openai" and self.client_openai:
                    formatted_msgs = [{"role": "system", "content": sys_prompt}] + messages
                    stream = await self.client_openai.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=formatted_msgs,
                        stream=True
                    )
                    accumulated = ""
                    async for chunk in stream:
                        delta = chunk.choices[0].delta
                        if delta.content:
                            accumulated += delta.content
                            yield accumulated, ""
                    return

            except Exception as e:
                logger.warning(f"Modelo '{current_model}' falhou com erro: {e}. Tentando fallback...")
                last_error = e
                continue

        # Se todos os modelos falharem
        yield f"❌ Todos os provedores falharam ao responder. Erro final: {last_error}", ""

llm_router = LLMRouter()
