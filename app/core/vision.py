"""
Multi-Modal Vision Analysis Module utilizing High-Speed Gemini & Fallback Engines.
"""
import io
import base64
import logging
from PIL import Image
from openai import AsyncOpenAI
from app.config import settings

logger = logging.getLogger(__name__)

class VisionAnalyzer:
    async def analyze_image(self, image_bytes: io.BytesIO, prompt: str = "Descreva e analise detalhadamente esta imagem:") -> str:
        """Analisa a imagem enviada usando Gemini Flash (gratuito) com fallback para OpenAI."""
        
        # 1. GOOGLE GEMINI FLASH (Alta Velocidade e Gratuito)
        if settings.GEMINI_API_KEY:
            try:
                image_bytes.seek(0)
                base64_image = base64.b64encode(image_bytes.read()).decode("utf-8")
                client = AsyncOpenAI(
                    api_key=settings.GEMINI_API_KEY,
                    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
                )
                
                res = await client.chat.completions.create(
                    model="gemini-3.6-flash",
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
                logger.warning(f"Falha na visão via Gemini: {e}")

        # 2. OPENAI GPT-4o-mini (Fallback)
        if settings.OPENAI_API_KEY:
            try:
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
