"""
Dynamic Visual Animation and Loading Frames Engine for Telegram (ChatGPT / Gemini UI Experience).
Provides animated status frames, pulsating cursors, and state transitions.
"""
import asyncio
import logging
from typing import List
from telegram import Message
from telegram.constants import ParseMode
from telegram.error import BadRequest

logger = logging.getLogger(__name__)

ANIMATION_PRESETS = {
    "thinking": [
        "✨ *Pensando...*",
        "🧠 *Conectando neurônios...*",
        "⚡ *Formulando raciocínio...*",
        "🔮 *Sintetizando resposta...*",
    ],
    "web_search": [
        "🌐 *Conectando à internet ao vivo...*",
        "🔍 *Varrendo portais e notícias em tempo real...*",
        "⚡ *Sintetizando fatos recentes...*",
        "✨ *Preparando síntese informativa...*",
    ],
    "trends_x": [
        "🔥 *Conectando ao feed do X (Twitter) Brasil...*",
        "📊 *Mapeando tópicos e hashtags mais comentadas...*",
        "⚡ *Analisando volume de tweets e repercussão...*",
        "✨ *Estruturando destaques do momento...*",
    ],
    "reading_url": [
        "🔗 *Conectando à página web...*",
        "📄 *Extraindo artigos, tabelas e texto limpo...*",
        "🧠 *Analisando conteúdo da página...*",
    ],
    "vision": [
        "👁️ *Carregando imagem...*",
        "🔬 *Escaneando pixels com Visão Computacional...*",
        "✨ *Reconhecendo objetos, texto e contexto...*",
    ],
    "voice": [
        "🎙️ *Ouvindo áudio...*",
        "⚡ *Transcrevendo fala em alta precisão...*",
        "🧠 *Interpretando mensagem...*",
    ],
    "document": [
        "📑 *Abrindo documento anexado...*",
        "🔍 *Extraindo texto, tabelas e código...*",
        "🧠 *Analisando estrutura do arquivo...*",
    ],
    "image_gen": [
        "🎨 *Conectando ao motor Flux.1 HD...*",
        "🖌️ *Desenhando cena e texturas em alta resolução...*",
        "✨ *Aplicando iluminação, profundidade e detalhes...*",
        "🚀 *Finalizando renderização em HD...*",
    ],
}

class AnimatedLoader:
    """Controla o ciclo de vida de uma animação de carregamento visual no Telegram."""
    def __init__(self, message: Message, preset: str = "thinking", interval: float = 1.2):
        self.message = message
        self.frames: List[str] = ANIMATION_PRESETS.get(preset, ANIMATION_PRESETS["thinking"])
        self.interval = interval
        self.stop_event = asyncio.Event()
        self.task = None

    async def _loop(self):
        idx = 0
        try:
            while not self.stop_event.is_set():
                frame = self.frames[idx % len(self.frames)]
                try:
                    await self.message.edit_text(frame, parse_mode=ParseMode.MARKDOWN)
                except BadRequest:
                    pass
                except Exception:
                    pass
                
                idx += 1
                try:
                    await asyncio.wait_for(self.stop_event.wait(), timeout=self.interval)
                except asyncio.TimeoutError:
                    pass
        except asyncio.CancelledError:
            pass

    def start(self):
        self.task = asyncio.create_task(self._loop())
        return self

    async def stop(self):
        self.stop_event.set()
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass

    async def switch_preset(self, new_preset: str):
        """Altera os frames de animação dinamicamente (ex: de pensando para buscando na web)."""
        self.frames = ANIMATION_PRESETS.get(new_preset, ANIMATION_PRESETS["thinking"])
