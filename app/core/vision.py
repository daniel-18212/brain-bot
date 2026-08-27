"""
Multi-Modal Vision Analysis Module utilizing Free-Tier Gemini & Fallback Engines.
"""
import io
import logging
from PIL import Image
import google.generativeai as genai
from openai import AsyncOpenAI
from app.config import settings

logger = logging.getLogger(__name__)

class VisionAnalyzer:
    async def analyze_image(self, image_bytes: io.BytesIO, prompt: str = "Descreva e analise detalhadamente esta imagem:") -> str:
        """Analisa a imagem enviada usando Gemini Flash (gratuito) com fallback para OpenAI."""
        
        # 1. GOOGLE GEMINI FLASH (Melhor e Gratuito)
        if settings.GEMINI_API_KEY:
            try:
                image = Image.open(image_bytes)
                model = genai.GenerativeModel("gemini-2.0-flash")
                response = await model.generate_content_async([prompt, image])
                return response.text
            except Exception as e:
                logger.warning(f"Falha na visão via Gemini: {e}")

        # 2. OPENAI GPT-4o-mini (Fallback)
        if settings.OPENAI_API_KEY:
            try:
                import base64
                image_bytes.seek(0)
                base64_image = base64.b64encode(image_bytes.read()).decode("utf-8")
                client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                
                res = await client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                                }
                            ]
                        }
                    ]
                )
                return res.choices[0].message.content
            except Exception as e:
                logger.error(f"Falha na visão via OpenAI: {e}")

        return "❌ Nenhum provedor com suporte a visão (Gemini / OpenAI) está configurado no .env."

vision_analyzer = VisionAnalyzer()
