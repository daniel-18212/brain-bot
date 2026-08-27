"""
High-Speed Audio Transcription Module using Free-Tier Groq Whisper-Large-V3.
"""
import io
import logging
from groq import AsyncGroq
from openai import AsyncOpenAI
from app.config import settings

logger = logging.getLogger(__name__)

class AudioTranscriber:
    def __init__(self):
        self.groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY) if settings.GROQ_API_KEY else None
        self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None

    async def transcribe(self, audio_bytes: io.BytesIO, filename: str = "voice.ogg") -> str:
        """Transcreve áudio com velocidade recorde via Groq Whisper ou OpenAI."""
        
        # 1. GROQ WHISPER (100% Grátis e resposta em < 500ms)
        if self.groq_client:
            try:
                audio_bytes.seek(0)
                transcription = await self.groq_client.audio.transcriptions.create(
                    file=(filename, audio_bytes.read()),
                    model="whisper-large-v3",
                    response_format="text"
                )
                return transcription
            except Exception as e:
                logger.warning(f"Falha no Groq Whisper: {e}")

        # 2. OPENAI WHISPER (Fallback)
        if self.openai_client:
            try:
                audio_bytes.seek(0)
                transcription = await self.openai_client.audio.transcriptions.create(
                    file=(filename, audio_bytes.read()),
                    model="whisper-1"
                )
                return transcription.text
            except Exception as e:
                logger.error(f"Falha no OpenAI Whisper: {e}")

        return "❌ Para transcrever áudios, configure a chave gratuita GROQ_API_KEY no .env."

audio_transcriber = AudioTranscriber()
