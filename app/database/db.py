"""
Institutional-Grade Asynchronous SQLite Database Layer.
Supports WAL Mode, Multi-Tenancy, Tier Quotas, Live System Settings, and Audit Logs.
"""
from datetime import datetime, date
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
        await db.execute("PRAGMA busy_timeout=5000;")
        return db

    async def init_db(self) -> None:
        """Inicializa esquema corporativo e tabelas de administração."""
        async with await self.get_connection() as db:
            # Tabela de Usuários com Tier, Cotas e Status
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    role TEXT DEFAULT 'user',          -- 'admin' ou 'user'
                    status TEXT DEFAULT 'active',      -- 'active', 'banned'
                    tier TEXT DEFAULT 'free',          -- 'free', 'pro', 'unlimited'
                    selected_model TEXT DEFAULT 'gemini',
                    custom_system_prompt TEXT,
                    daily_requests_count INTEGER DEFAULT 0,
                    last_request_date TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Tabela de Mensagens e Conversas
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

            # Métricas e Auditoria
            await db.execute("""
                CREATE TABLE IF NOT EXISTS usage_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    action_type TEXT NOT NULL,         -- 'text', 'vision', 'audio', 'web_search', 'image_gen'
                    model TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            """)

            # Configurações Dinâmicas do Sistema em Tempo de Execução
            await db.execute("""
                CREATE TABLE IF NOT EXISTS system_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Índices de Alta Performance
            await db.execute("CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages(user_id, id);")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_usage_user_id ON usage_metrics(user_id, created_at);")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_users_status ON users(status, role);")

            # Garante que o Admin Principal tenha role 'admin'
            if settings.ADMIN_USER_ID:
                await db.execute(
                    """
                    INSERT INTO users (user_id, role, tier) VALUES (?, 'admin', 'unlimited')
                    ON CONFLICT(user_id) DO UPDATE SET role = 'admin', tier = 'unlimited'
                    """,
                    (settings.ADMIN_USER_ID,)
                )

            await db.commit()
            logger.info(f"Institutional Database initialized at {self.db_path}")

    # --- Operações de Usuário ---

    async def get_or_create_user(self, user_id: int, username: str = "", first_name: str = "") -> dict:
        today_str = str(date.today())
        async with await self.get_connection() as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    user_dict = dict(row)
                    # Reset diário de cota se mudou o dia
                    if user_dict.get("last_request_date") != today_str:
                        await db.execute(
                            "UPDATE users SET daily_requests_count = 0, last_request_date = ? WHERE user_id = ?",
                            (today_str, user_id)
                        )
                        user_dict["daily_requests_count"] = 0
                    
                    await db.execute(
                        "UPDATE users SET last_active_at = CURRENT_TIMESTAMP, username = ?, first_name = ? WHERE user_id = ?",
                        (username, first_name, user_id)
                    )
                    await db.commit()
                    return user_dict

            # Cadastro de Novo Usuário
            role = "admin" if user_id == settings.ADMIN_USER_ID else "user"
            tier = "unlimited" if role == "admin" else "free"
            
            await db.execute(
                """
                INSERT INTO users (user_id, username, first_name, role, tier, selected_model, last_request_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, username, first_name, role, tier, settings.DEFAULT_MODEL, today_str)
            )
            await db.commit()
            return {
                "user_id": user_id,
                "username": username,
                "first_name": first_name,
                "role": role,
                "status": "active",
                "tier": tier,
                "selected_model": settings.DEFAULT_MODEL,
                "custom_system_prompt": None,
                "daily_requests_count": 0,
                "last_request_date": today_str
            }

    async def increment_user_quota(self, user_id: int) -> None:
        today_str = str(date.today())
        async with await self.get_connection() as db:
            await db.execute(
                """
                UPDATE users 
                SET daily_requests_count = daily_requests_count + 1, last_request_date = ?
                WHERE user_id = ?
                """,
                (today_str, user_id)
            )
            await db.commit()

    async def update_user_model(self, user_id: int, model: str) -> None:
        async with await self.get_connection() as db:
            await db.execute("UPDATE users SET selected_model = ? WHERE user_id = ?", (model, user_id))
            await db.commit()

    async def update_user_system_prompt(self, user_id: int, prompt: str | None) -> None:
        async with await self.get_connection() as db:
            await db.execute("UPDATE users SET custom_system_prompt = ? WHERE user_id = ?", (prompt, user_id))
            await db.commit()

    async def set_user_status(self, user_id: int, status: str) -> None:
        async with await self.get_connection() as db:
            await db.execute("UPDATE users SET status = ? WHERE user_id = ?", (status, user_id))
            await db.commit()

    async def set_user_tier(self, user_id: int, tier: str) -> None:
        async with await self.get_connection() as db:
            await db.execute("UPDATE users SET tier = ? WHERE user_id = ?", (tier, user_id))
            await db.commit()

    # --- Mensagens e Histórico ---

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

    # --- Métricas e Administração ---

    async def record_usage(self, user_id: int, action_type: str, model: str = "") -> None:
        async with await self.get_connection() as db:
            await db.execute(
                "INSERT INTO usage_metrics (user_id, action_type, model) VALUES (?, ?, ?)",
                (user_id, action_type, model)
            )
            await db.commit()

    async def get_admin_dashboard_stats(self) -> dict:
        """Coleta estatísticas completas de negócio para o painel de controle do Telegram."""
        async with await self.get_connection() as db:
            async with db.execute("SELECT COUNT(*) FROM users") as c1:
                total_users = (await c1.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM users WHERE status = 'active'") as c2:
                active_users = (await c2.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM users WHERE tier = 'pro' OR tier = 'unlimited'") as c3:
                pro_users = (await c3.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM messages") as c4:
                total_messages = (await c4.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM messages WHERE DATE(created_at) = DATE('now')") as c5:
                messages_today = (await c5.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM usage_metrics WHERE action_type = 'image_gen'") as c6:
                images_gen = (await c6.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM usage_metrics WHERE action_type = 'web_search'") as c7:
                web_searches = (await c7.fetchone())[0]

            return {
                "total_users": total_users,
                "active_users": active_users,
                "pro_users": pro_users,
                "total_messages": total_messages,
                "messages_today": messages_today,
                "images_gen": images_gen,
                "web_searches": web_searches
            }

    async def get_all_users_for_broadcast(self) -> list[int]:
        """Retorna todos os IDs de usuários ativos para transmissão de mensagens."""
        async with await self.get_connection() as db:
            async with db.execute("SELECT user_id FROM users WHERE status = 'active'") as cursor:
                rows = await cursor.fetchall()
                return [r[0] for r in rows]

    async def get_top_users(self, limit: int = 10) -> list[dict]:
        async with await self.get_connection() as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT u.user_id, u.username, u.first_name, u.tier, u.status, COUNT(m.id) as message_count
                FROM users u
                LEFT JOIN messages m ON u.user_id = m.user_id
                GROUP BY u.user_id
                ORDER BY message_count DESC
                LIMIT ?
                """,
                (limit,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def get_system_setting(self, key: str, default: str = "") -> str:
        async with await self.get_connection() as db:
            async with db.execute("SELECT value FROM system_settings WHERE key = ?", (key,)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else default

    async def set_system_setting(self, key: str, value: str) -> None:
        async with await self.get_connection() as db:
            await db.execute(
                """
                INSERT INTO system_settings (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
                """,
                (key, value)
            )
            await db.commit()

db = Database()
