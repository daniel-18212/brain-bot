"""
Unified Multi-Provider LLM Router with Auto-Failover, Resilient HTTPX Pool, and Live Web Grounding.
"""
from datetime import datetime
import logging
from typing import AsyncGenerator, Tuple
import httpx
from openai import AsyncOpenAI
from app.config import settings
from app.core.resilience import circuit_breaker

logger = logging.getLogger(__name__)

def get_system_prompt_with_live_time(custom_prompt: str | None = None) -> str:
    """Gera o prompt do sistema injetando a data e hora atual do mundo real com tom humano e conversacional."""
    now_str = datetime.now().strftime("%d de %B de %Y, %H:%M")
    
    base_prompt = custom_prompt or (
        "Você é o BrainBot, um assistente de IA extremamente inteligente, natural, simpático e direto ao ponto — com a mesma fluidez conversacional do ChatGPT e do Gemini.\n\n"
        "DIRETRIZES DE PERSONALIDADE E ESTILO:\n"
        "1. **Tom Humano e Natural:** Converse como uma pessoa real e articulada. Seja caloroso, direto e perspicaz. Evite soar engessado, corporativo em excesso ou robótico.\n"
        "2. **Zero Clichês de Robô:** NUNCA use introduções ou encerramentos repetitivos como 'Com base nas informações...', 'Como uma IA...', 'Segue abaixo...', ou 'Espero ter ajudado!'. Vá direto ao que interessa com naturalidade.\n"
        "3. **Respostas Proporcionais:** Adapte a resposta ao contexto. Se o usuário mandar uma saudação simples ou pergunta rápida, responda de forma leve e rápida. Se pedir uma análise profunda, entregue uma resposta completa e estruturada.\n"
        "4. **Integração Web Transparente:** Quando houver dados da web ou notícias em tempo real no contexto, converse sobre eles como alguém bem informado que acabou de ler a respeito, citando detalhes de forma fluida sem parecer um relatório mecânico.\n"
        "5. **Markdown Orgânico:** Use negrito, tópicos e formatação apenas quando realmente tornar a leitura agradável e clara no Telegram, sem poluir visualmente."
    )
    
    time_context = f"\n\n[Contexto temporal: Hoje é {now_str} (Horário de Brasília)]."
    return base_prompt + time_context

class LLMRouter:
    AVAILABLE_MODELS = {
        "auto": {
            "name": "✨ Auto (Roteamento Dinâmico)",
            "provider": "Multi-Engine",
            "description": "Escolhe e alterna automaticamente o melhor motor com auto-recuperação.",
            "badge": "✨ Auto Engine"
        },
        "deepseek": {
            "name": "⚡ DeepSeek V4/V3",
            "provider": "DeepSeek API",
            "description": "Seu motor principal de programação, lógica e textos longos.",
            "badge": "⚡ DeepSeek V4"
        },
        "deepseek-r1": {
            "name": "🧠 DeepSeek R1 Oficial",
            "provider": "DeepSeek API",
            "description": "Raciocínio lógico e matemático formal com encadeamento de pensamentos.",
            "badge": "🧠 DeepSeek R1"
        },
        "gemini": {
            "name": "⚡ Gemini 3.6 Flash",
            "provider": "Google AI (Grátis)",
            "description": "Velocidade máxima, multimodal e contexto de 1 milhão de tokens.",
            "badge": "⚡ Gemini 3.6 Flash"
        },
        "groq-llama": {
            "name": "🚀 GPT-OSS 120B (Groq)",
            "provider": "Groq Cloud (Grátis)",
            "description": "Motor de 120 bilhões de parâmetros rodando a 300+ tokens/segundo.",
            "badge": "🚀 GPT-OSS 120B (Groq)"
        },
        "github-gpt4o": {
            "name": "🟢 GPT-4o Oficial",
            "provider": "GitHub Models (Grátis)",
            "description": "O modelo principal da OpenAI oficial e gratuito via Azure/GitHub.",
            "badge": "🟢 GPT-4o"
        }
    }

    def __init__(self):
        # Pool HTTPX com alta resiliência e keep-alive persistente
        self.http_client = httpx.AsyncClient(
            limits=httpx.Limits(max_keepalive_connections=30, max_connections=100),
            timeout=httpx.Timeout(connect=15.0, read=60.0, write=20.0, pool=20.0)
        )

        # 1. DeepSeek Client
        self.client_deepseek = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com",
            http_client=self.http_client
        ) if settings.DEEPSEEK_API_KEY else None

        # 2. Google Gemini Client (OpenAI-compatible)
        self.client_gemini = AsyncOpenAI(
            api_key=settings.GEMINI_API_KEY,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            http_client=self.http_client
        ) if settings.GEMINI_API_KEY else None

        # 3. Groq Client
        self.client_groq = AsyncOpenAI(
            api_key=settings.GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1",
            http_client=self.http_client
        ) if settings.GROQ_API_KEY else None

        # 4. GitHub Models (Azure AI)
        self.client_github = AsyncOpenAI(
            api_key=settings.GITHUB_TOKEN,
            base_url="https://models.inference.ai.azure.com",
            http_client=self.http_client
        ) if settings.GITHUB_TOKEN else None

    async def stream_response(
        self,
        model_key: str,
        messages: list[dict],
        system_prompt: str | None = None
    ) -> AsyncGenerator[Tuple[str, str, str, str], None]:
        """
        Gera resposta via streaming com proteção de Circuit Breaker, Fallback Transparente e Badges.
        Retorna tupla: (texto_acumulado, raciocinio_acumulado, modelo_usado, aviso_fallback)
        """
        sys_prompt = get_system_prompt_with_live_time(system_prompt)
        
        if model_key == "auto":
            fallback_order = ["deepseek", "gemini", "groq-llama", "github-gpt4o"]
        else:
            fallback_order = [model_key, "deepseek", "gemini", "groq-llama", "github-gpt4o"]
            
        unique_order = list(dict.fromkeys(fallback_order))
        last_error = None

        for current_model in unique_order:
            if not circuit_breaker.is_available(current_model):
                logger.info(f"Pulando modelo '{current_model}' (Circuit Breaker aberto).")
                continue

            fallback_notice = ""
            if model_key != "auto" and current_model != model_key:
                req_name = self.AVAILABLE_MODELS.get(model_key, {}).get("name", model_key)
                curr_name = self.AVAILABLE_MODELS.get(current_model, {}).get("name", current_model)
                fallback_notice = f"⚡ _[{req_name} oscilou → Alternado automaticamente para {curr_name}]_"

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
                        yield accumulated_content, accumulated_reasoning, current_model, fallback_notice
                    
                    circuit_breaker.record_success(current_model)
                    return

                # 2. GOOGLE GEMINI (3.6 Flash Oficial - Grátis)
                elif current_model in ("gemini", "gemini-pro") and self.client_gemini:
                    formatted_msgs = [{"role": "system", "content": sys_prompt}] + messages
                    stream = await self.client_gemini.chat.completions.create(
                        model="gemini-3.6-flash",
                        messages=formatted_msgs,
                        stream=True
                    )
                    
                    accumulated_content = ""
                    async for chunk in stream:
                        delta = chunk.choices[0].delta
                        if delta.content:
                            accumulated_content += delta.content
                        yield accumulated_content, "", current_model, fallback_notice
                    
                    circuit_breaker.record_success(current_model)
                    return

                # 3. GROQ CLOUD (GPT-OSS 120B / Llama 3.3 70B - 300+ tok/s)
                elif current_model == "groq-llama" and self.client_groq:
                    formatted_msgs = [{"role": "system", "content": sys_prompt}] + messages
                    stream = await self.client_groq.chat.completions.create(
                        model="openai/gpt-oss-120b",
                        messages=formatted_msgs,
                        stream=True
                    )
                    
                    accumulated_content = ""
                    async for chunk in stream:
                        delta = chunk.choices[0].delta
                        if delta.content:
                            accumulated_content += delta.content
                        yield accumulated_content, "", current_model, fallback_notice
                    
                    circuit_breaker.record_success(current_model)
                    return

                # 4. GITHUB MODELS (GPT-4o Oficial - Grátis)
                elif current_model in ("github-gpt4o", "github-gpt4o-mini") and self.client_github:
                    gh_model = "gpt-4o-mini" if current_model == "github-gpt4o-mini" else "gpt-4o"
                    formatted_msgs = [{"role": "system", "content": sys_prompt}] + messages
                    stream = await self.client_github.chat.completions.create(
                        model=gh_model,
                        messages=formatted_msgs,
                        stream=True
                    )
                    
                    accumulated_content = ""
                    async for chunk in stream:
                        delta = chunk.choices[0].delta
                        if delta.content:
                            accumulated_content += delta.content
                        yield accumulated_content, "", current_model, fallback_notice
                    
                    circuit_breaker.record_success(current_model)
                    return

            except Exception as e:
                circuit_breaker.record_failure(current_model)
                logger.warning(f"⚠️ Falha no motor '{current_model}': {e}. Acionando fallback...")
                last_error = e

        logger.error(f"Todos os motores de IA falharam: {last_error}")
        raise RuntimeError(f"Todos os provedores de IA estão temporariamente indisponíveis: {last_error}")

llm_router = LLMRouter()
