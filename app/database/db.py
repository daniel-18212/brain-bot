"""
Asynchronous SQLite Database Management Layer with WAL Mode and Schema Migrations.
"""
from datetime import datetime
import logging
from pathlib import Path
import aiosqlite
from app.config import settings

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: Path = settings.DATABASE_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    async def get_connection(self) -> aiosqlite.Connection:
        db = await aiosqlite.connect(self.db_path)
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("PRAGMA synchronous=NORMAL;")
        await db.execute("PRAGMA foreign_keys=ON;")
        return db

    async def init_db(self) -> None:
        """Inicializa tabelas e índices necessários."""
        async with await self.get_connection() as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    selected_model TEXT DEFAULT 'gemini',
                    custom_system_prompt TEXT,
                    tokens_used INTEGER DEFAULT 0,
                    tier TEXT DEFAULT 'free',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    model_used TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS usage_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    action_type TEXT NOT NULL,
                    model TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            """)
            # Índices para alta performance
            await db.execute("CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages(user_id, id);")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_usage_user_id ON usage_metrics(user_id, created_at);")
            await db.commit()
            logger.info(f"Database pronto e configurado em {self.db_path}")

    async def get_or_create_user(self, user_id: int, username: str = "", first_name: str = "") -> dict:
        """Busca usuário existente ou cadastra novo."""
        async with await self.get_connection() as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    await db.execute(
                        "UPDATE users SET last_active_at = CURRENT_TIMESTAMP, username = ?, first_name = ? WHERE user_id = ?",
                        (username, first_name, user_id)
                    )
                    await db.commit()
                    return dict(row)

            # Inserção de novo usuário
            await db.execute(
                """
                INSERT INTO users (user_id, username, first_name, selected_model)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, username, first_name, settings.DEFAULT_MODEL)
            )
            await db.commit()
            return {
                "user_id": user_id,
                "username": username,
                "first_name": first_name,
                "selected_model": settings.DEFAULT_MODEL,
                "custom_system_prompt": None,
                "tokens_used": 0,
                "tier": "free"
            }

    async def update_user_model(self, user_id: int, model: str) -> None:
        async with await self.get_connection() as db:
            await db.execute("UPDATE users SET selected_model = ? WHERE user_id = ?", (model, user_id))
            await db.commit()

    async def update_user_system_prompt(self, user_id: int, prompt: str | None) -> None:
        async with await self.get_connection() as db:
            await db.execute("UPDATE users SET custom_system_prompt = ? WHERE user_id = ?", (prompt, user_id))
            await db.commit()

    async def save_message(self, user_id: int, role: str, content: str, model_used: str = "") -> None:
        async with await self.get_connection() as db:
            await db.execute(
                "INSERT INTO messages (user_id, role, content, model_used) VALUES (?, ?, ?, ?)",
                (user_id, role, content, model_used)
            )
            await db.commit()

    async def get_context_history(self, user_id: int, limit: int = settings.MAX_CONTEXT_TURNS) -> list[dict]:
        async with await self.get_connection() as db:
            async with db.execute(
                """
                SELECT role, content FROM (
                    SELECT id, role, content FROM messages
                    WHERE user_id = ?
                    ORDER BY id DESC LIMIT ?
                ) ORDER BY id ASC
                """,
                (user_id, limit)
            ) as cursor:
                rows = await cursor.fetchall()
                return [{"role": r[0], "content": r[1]} for r in rows]

    async def clear_history(self, user_id: int) -> None:
        async with await self.get_connection() as db:
            await db.execute("DELETE FROM messages WHERE user_id = ?", (user_id,))
            await db.commit()

    async def record_usage(self, user_id: int, action_type: str, model: str = "") -> None:
        async with await self.get_connection() as db:
            await db.execute(
                "INSERT INTO usage_metrics (user_id, action_type, model) VALUES (?, ?, ?)",
                (user_id, action_type, model)
            )
            await db.commit()

    async def get_user_stats(self, user_id: int) -> dict:
        async with await self.get_connection() as db:
            async with db.execute("SELECT COUNT(*) FROM messages WHERE user_id = ?", (user_id,)) as cur1:
                total_messages = (await cur1.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM usage_metrics WHERE user_id = ? AND action_type = 'image_gen'", (user_id,)) as cur2:
                total_images = (await cur2.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM usage_metrics WHERE user_id = ? AND action_type = 'web_search'", (user_id,)) as cur3:
                total_searches = (await cur3.fetchone())[0]
            
            return {
                "total_messages": total_messages,
                "total_images": total_images,
                "total_searches": total_searches
            }

db = Database()
