"""
Application Configuration and Settings Validation Module.
"""
from functools import lru_cache
import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega arquivo .env da raiz do projeto
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

class Settings:
    def __init__(self):
        self.BASE_DIR: Path = BASE_DIR
        self.TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        self.ADMIN_USER_ID: int = int(os.getenv("ADMIN_USER_ID", "0"))
        self.ACCESS_MODE: str = os.getenv("ACCESS_MODE", "PRIVATE").upper()
        
        whitelist_raw = os.getenv("WHITELIST_USERS", "")
        self.WHITELIST_USERS: set[int] = {
            int(uid.strip()) for uid in whitelist_raw.split(",") if uid.strip().isdigit()
        }
        if self.ADMIN_USER_ID:
            self.WHITELIST_USERS.add(self.ADMIN_USER_ID)

        # Provedores de IA
        self.DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "").strip()
        self.GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "").strip()
        self.GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "").strip()
        self.OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "").strip()
        self.OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "").strip()

        # Preferências
        self.DEFAULT_MODEL: str = os.getenv("DEFAULT_MODEL", "gemini").lower()
        db_path_env = os.getenv("DATABASE_PATH", "data/brain_bot.sqlite")
        self.DATABASE_PATH: Path = BASE_DIR / db_path_env if not os.path.isabs(db_path_env) else Path(db_path_env)
        self.MAX_CONTEXT_TURNS: int = int(os.getenv("MAX_CONTEXT_TURNS", "20"))
        self.STREAMING_THROTTLE_SECONDS: float = float(os.getenv("STREAMING_THROTTLE_SECONDS", "1.2"))
        self.LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()

    def validate(self) -> None:
        """Valida se as configurações mínimas para inicialização estão presentes."""
        if not self.TELEGRAM_BOT_TOKEN or self.TELEGRAM_BOT_TOKEN == "your_telegram_bot_token_here":
            raise ValueError(
                "❌ TELEGRAM_BOT_TOKEN não configurado no .env! "
                "Crie seu bot no @BotFather e adicione o token no arquivo .env."
            )
        
        has_any_ai_key = any([
            self.DEEPSEEK_API_KEY,
            self.GEMINI_API_KEY,
            self.GROQ_API_KEY,
            self.OPENROUTER_API_KEY,
            self.OPENAI_API_KEY
        ])
        
        if not has_any_ai_key:
            raise ValueError(
                "❌ Nenhuma chave de API de IA foi configurada no .env! "
                "Configure ao menos uma (GEMINI_API_KEY, GROQ_API_KEY ou DEEPSEEK_API_KEY)."
            )

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
