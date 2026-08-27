"""
Application Configuration and Settings Validation Module (Elite Top 4 Providers).
"""
from functools import lru_cache
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

class Settings:
    def __init__(self):
        self.BASE_DIR: Path = BASE_DIR
        self.TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        self.ADMIN_USER_ID: int = int(os.getenv("ADMIN_USER_ID", "0"))
        self.ADMIN_CONTACT: str = os.getenv("ADMIN_CONTACT", "@turion").strip()
        self.ACCESS_MODE: str = os.getenv("ACCESS_MODE", "WHITELIST").upper()
        
        whitelist_raw = os.getenv("WHITELIST_USERS", "")
        self.WHITELIST_USERS: set[int] = {
            int(uid.strip()) for uid in whitelist_raw.split(",") if uid.strip().isdigit()
        }
        if self.ADMIN_USER_ID:
            self.WHITELIST_USERS.add(self.ADMIN_USER_ID)

        # === TOP 4 PROVEDORES DE ELITE ===
        self.DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "").strip()
        self.GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "").strip()
        self.GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "").strip()
        self.GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "").strip()
        self.OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "").strip()

        # Preferências, Cotas e Limites
        self.DEFAULT_MODEL: str = os.getenv("DEFAULT_MODEL", "deepseek").lower()
        db_path_env = os.getenv("DATABASE_PATH", "data/brain_bot.sqlite")
        self.DATABASE_PATH: Path = BASE_DIR / db_path_env if not os.path.isabs(db_path_env) else Path(db_path_env)
        self.MAX_CONTEXT_TURNS: int = int(os.getenv("MAX_CONTEXT_TURNS", "20"))
        self.STREAMING_THROTTLE_SECONDS: float = float(os.getenv("STREAMING_THROTTLE_SECONDS", "1.2"))
        self.LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
        self.HEALTH_PORT: int = int(os.getenv("HEALTH_PORT", "8080"))

        # Cotas Diárias de Mensagens por Plano
        self.TIER_QUOTAS = {
            "free": 30,
            "pro": 200,
            "unlimited": 999999
        }

    def validate(self) -> None:
        if not self.TELEGRAM_BOT_TOKEN or self.TELEGRAM_BOT_TOKEN == "your_telegram_bot_token_here":
            raise ValueError(
                "❌ TELEGRAM_BOT_TOKEN não configurado no .env! "
                "Crie seu bot no @BotFather e adicione o token no arquivo .env."
            )
        
        has_any_key = any([
            self.DEEPSEEK_API_KEY,
            self.GEMINI_API_KEY,
            self.GROQ_API_KEY,
            self.GITHUB_TOKEN,
            self.OPENAI_API_KEY
        ])
        
        if not has_any_key:
            raise ValueError(
                "❌ Nenhuma chave de IA configurada! "
                "Configure ao menos uma chave no .env."
            )

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
