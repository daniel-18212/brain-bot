"""
High-Speed Audio Transcription Module using Free-Tier Groq Whisper-Large-V3.
"""
import io
import logging
from openai import AsyncOpenAI
from app.config import settings

logger = logging.getLogger(__name__)

class AudioTranscriber:
    async def transcribe(self, audio_bytes: io.BytesIO, filename: str = "voice.ogg") -> str:
        """Transcreve áudio com velocidade recorde via Groq Whisper ou OpenAI."""
        
        # 1. GROQ WHISPER (100% Grátis e resposta em < 500ms)
        if settings.GROQ_API_KEY:
            try:
                audio_bytes.seek(0)
                client = AsyncOpenAI(
                    api_key=settings.GROQ_API_KEY,
                    base_url="https://api.groq.com/openai/v1"
                )
                transcription = await client.audio.transcriptions.create(
                    file=(filename, audio_bytes.read()),
                    model="whisper-large-v3-turbo",
                    response_format="text"
                )
                return str(transcription)
            except Exception as e:
                logger.warning(f"Falha no Groq Whisper: {e}")

        # 2. OPENAI WHISPER (Fallback)
        if settings.OPENAI_API_KEY:
            try:
                audio_bytes.seek(0)
                client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                transcription = await client.audio.transcriptions.create(
                    file=(filename, audio_bytes.read()),
                    model="whisper-1"
                )
                return transcription.text
            except Exception as e:
                logger.error(f"Falha no OpenAI Whisper: {e}")

        return "❌ Para transcrever áudios, configure a chave gratuita GROQ_API_KEY no .env."

audio_transcriber = AudioTranscriber()
