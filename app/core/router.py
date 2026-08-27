"""
Unified Multi-Provider LLM Router for Top 4 Elite Engines:
1. DeepSeek API (V4 / V3 & R1 Reasoner)
2. Google Gemini (2.0 Flash & 1.5 Pro - Free Tier)
3. Groq Cloud (Llama 3.3 70B & DeepSeek R1 Distill - Free Tier)
4. GitHub Models / Azure AI (Official GPT-4o & GPT-4o Mini - Free Tier)
"""
from typing import AsyncGenerator
import logging
from openai import AsyncOpenAI
import google.generativeai as genai
from app.config import settings
from app.core.resilience import circuit_breaker

logger = logging.getLogger(__name__)

if settings.GEMINI_API_KEY:
    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
    except Exception as e:
        logger.warning(f"Aviso na inicialização do Gemini: {e}")

class LLMRouter:
    DEFAULT_SYSTEM_PROMPT = """Você é o BrainBot, um assistente de inteligência artificial de elite, versátil, ultra-rápido, perspicaz, amigável e de alta precisão.
- Responda sempre em português fluente (a menos que o usuário solicite outro idioma).
- Use formatação Markdown elegante e limpa: títulos, negrito, listas e blocos de código com a linguagem especificada.
- Você possui capacidade total de ler, analisar e raciocinar sobre documentos (PDFs, planilhas, arquivos de texto e código) e imagens que forem fornecidos no histórico de mensagens.
- Se forem fornecidos dados em tempo real da Web ou conteúdo de arquivos no histórico, incorpore essas informações diretamente em sua resposta de forma natural e precisa.
- Seja proativo, direto e acolhedor, fornecendo soluções de nível sênior sem hesitação."""

    AVAILABLE_MODELS = {
        "deepseek": {
            "name": "⚡ DeepSeek V4/V3",
            "provider": "DeepSeek API",
            "description": "Seu motor principal de programação, lógica e textos longos."
        },
        "deepseek-r1": {
            "name": "🧠 DeepSeek R1 Oficial",
            "provider": "DeepSeek API",
            "description": "Raciocínio lógico e matemático formal com encadeamento de pensamentos."
        },
        "gemini": {
            "name": "⚡ Gemini 2.0 Flash",
            "provider": "Google (Grátis)",
            "description": "Velocidade máxima, multimodal e contexto de 1 milhão de tokens."
        },
        "gemini-pro": {
            "name": "🌟 Gemini 1.5 Pro",
            "provider": "Google (Grátis)",
            "description": "Análise aprofundada de documentos complexos e raciocínio multimodal."
        },
        "groq-llama": {
            "name": "🚀 Llama 3.3 70B",
            "provider": "Groq Cloud (Grátis)",
            "description": "Velocidade extrema de 300+ tokens/segundo em hardware LPU."
        },
        "github-gpt4o": {
            "name": "🟢 GPT-4o Oficial",
            "provider": "GitHub Models (Grátis)",
            "description": "O modelo principal da OpenAI oficial e gratuito via Azure/GitHub."
        },
        "github-gpt4o-mini": {
            "name": "🟢 GPT-4o Mini",
            "provider": "GitHub Models (Grátis)",
            "description": "Versão compacta, rápida e precisa do GPT-4o."
        }
    }

    def __init__(self):
        # 1. DeepSeek Client
        self.client_deepseek = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com"
        ) if settings.DEEPSEEK_API_KEY else None

        # 2. Groq Client
        self.client_groq = AsyncOpenAI(
            api_key=settings.GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1"
        ) if settings.GROQ_API_KEY else None

        # 3. GitHub Models (Azure AI)
        self.client_github = AsyncOpenAI(
            api_key=settings.GITHUB_TOKEN,
            base_url="https://models.inference.ai.azure.com"
        ) if settings.GITHUB_TOKEN else None

        # 4. OpenAI Direct Client (Opcional)
        self.client_openai = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY
        ) if settings.OPENAI_API_KEY else None

    async def stream_response(
        self,
        model_key: str,
        messages: list[dict],
        system_prompt: str | None = None
    ) -> AsyncGenerator[tuple[str, str], None]:
        """Gera resposta via streaming com proteção de Circuit Breaker e Fallback Chain."""
        sys_prompt = system_prompt or self.DEFAULT_SYSTEM_PROMPT
        
        fallback_order = [model_key, "deepseek", "gemini", "groq-llama", "github-gpt4o"]
        unique_order = list(dict.fromkeys(fallback_order))

        last_error = None
        for current_model in unique_order:
            if not circuit_breaker.is_available(current_model):
                logger.info(f"Pulando modelo '{current_model}' (Circuit Breaker aberto).")
                continue

            try:
                # 1. DEEPSEEK (V4/V3 e R1 Oficial)
                if current_model in ("deepseek", "deepseek-r1") and self.client_deepseek:
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
                    
                    circuit_breaker.record_success(current_model)
                    return

                # 2. GOOGLE GEMINI (2.0 Flash e 1.5 Pro - Grátis)
                elif current_model in ("gemini", "gemini-pro") and settings.GEMINI_API_KEY:
                    model_target = "gemini-2.0-flash" if current_model == "gemini" else "gemini-1.5-pro"
                    model = genai.GenerativeModel(
                        model_name=model_target,
                        system_instruction=sys_prompt
                    )
                    
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
                    
                    circuit_breaker.record_success(current_model)
                    return

                # 3. GROQ CLOUD (Llama 3.3 70B - Grátis)
                elif current_model == "groq-llama" and self.client_groq:
                    formatted_msgs = [{"role": "system", "content": sys_prompt}] + messages
                    stream = await self.client_groq.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=formatted_msgs,
                        stream=True
                    )
                    
                    accumulated = ""
                    async for chunk in stream:
                        delta = chunk.choices[0].delta
                        if delta.content:
                            accumulated += delta.content
                            yield accumulated, ""
                    
                    circuit_breaker.record_success(current_model)
                    return

                # 4. GITHUB MODELS (GPT-4o e GPT-4o-Mini Oficiais da OpenAI via Azure)
                elif current_model in ("github-gpt4o", "github-gpt4o-mini") and self.client_github:
                    gh_model = "gpt-4o" if current_model == "github-gpt4o" else "gpt-4o-mini"
                    formatted_msgs = [{"role": "system", "content": sys_prompt}] + messages
                    
                    stream = await self.client_github.chat.completions.create(
                        model=gh_model,
                        messages=formatted_msgs,
                        stream=True
                    )
                    
                    accumulated = ""
                    async for chunk in stream:
                        delta = chunk.choices[0].delta
                        if delta.content:
                            accumulated += delta.content
                            yield accumulated, ""
                    
                    circuit_breaker.record_success(current_model)
                    return

            except Exception as e:
                circuit_breaker.record_failure(current_model)
                logger.warning(f"Provedor '{current_model}' falhou com erro: {e}. Executando fallback...")
                last_error = e
                continue

        yield f"❌ Todos os provedores do Top 4 falharam ao responder. Erro final: {last_error}", ""

llm_router = LLMRouter()
