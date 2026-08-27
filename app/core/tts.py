"""
High-Definition Neural Text-to-Speech Module using Microsoft Edge Neural Voices.
100% Free, Zero-Config, Natural Brazilian Portuguese Voice.
"""
import io
import re
import logging
import edge_tts

logger = logging.getLogger(__name__)

class TextToSpeech:
    DEFAULT_VOICE = "pt-BR-AntonioNeural"  # Voz masculina natural brasileira
    # Alternativa: "pt-BR-FranciscaNeural" (Voz feminina natural)

    @staticmethod
    def clean_text_for_speech(text: str) -> str:
        """Limpa blocos de código, URLs e símbolos Markdown para a fala soar natural."""
        # Remove blocos de código ```...```
        cleaned = re.sub(r"```[\s\S]*?```", " [código omitido no áudio] ", text)
        # Remove links markdown [texto](url)
        cleaned = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", cleaned)
        # Remove URLs
        cleaned = re.sub(r"https?://\S+", "", cleaned)
        # Remove símbolos de formatação (*, _, `, ~, #)
        cleaned = re.sub(r"[*_`~#|>]", "", cleaned)
        # Limpa espaços e quebras excessivas
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        # Trunca para até 1500 caracteres para síntese de voz rápida e ágil
        if len(cleaned) > 1500:
            cleaned = cleaned[:1490] + "..."
        return cleaned

    async def generate_voice_bytes(self, text: str, voice: str | None = None) -> io.BytesIO | None:
        """Gera áudio OGG/MP3 em memória pronto para envio no Telegram como mensagem de voz."""
        clean_text = self.clean_text_for_speech(text)
        if not clean_text or len(clean_text) < 2:
            return None

        target_voice = voice or self.DEFAULT_VOICE
        try:
            communicate = edge_tts.Communicate(clean_text, target_voice)
            audio_buffer = io.BytesIO()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_buffer.write(chunk["data"])
            
            audio_buffer.seek(0)
            return audio_buffer
        except Exception as e:
            logger.error(f"Erro na síntese de voz Edge-TTS: {e}")
            return None

tts_engine = TextToSpeech()
