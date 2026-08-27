"""
Institutional-Grade Asynchronous SQLite Database Layer.
Supports Multi-Tenancy, Client Onboarding, Tier Quotas, Long-Term Memories, and System Settings.
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

    def get_connection(self):
        return aiosqlite.connect(self.db_path)

    async def init_db(self) -> None:
        """Inicializa esquema corporativo e tabelas de administração."""
        async with self.get_connection() as db:
            await db.execute("PRAGMA journal_mode=WAL;")
            await db.execute("PRAGMA synchronous=NORMAL;")
            await db.execute("PRAGMA foreign_keys=ON;")
            await db.execute("PRAGMA busy_timeout=5000;")

            # Tabela de Usuários e Clientes
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    role TEXT DEFAULT 'user',          -- 'admin' ou 'user'
                    status TEXT DEFAULT 'pending',     -- 'active', 'pending', 'banned'
                    tier TEXT DEFAULT 'free',          -- 'free', 'pro', 'unlimited'
                    selected_model TEXT DEFAULT 'deepseek',
                    custom_system_prompt TEXT,
                    voice_mode_enabled INTEGER DEFAULT 0,
                    daily_requests_count INTEGER DEFAULT 0,
                    last_request_date TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Tabela de Memórias Permanentes de Longo Prazo
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    memory_text TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            """)

            # Tabela de Mensagens
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
                    action_type TEXT NOT NULL,
                    model TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            """)

            # Configurações Dinâmicas do Sistema
            await db.execute("""
                CREATE TABLE IF NOT EXISTS system_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Índices de Alta Performance
            await db.execute("CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages(user_id, id);")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_memories_user_id ON user_memories(user_id);")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_usage_user_id ON usage_metrics(user_id, created_at);")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_users_status ON users(status, role);")

            # Auto-Migração Dinâmica de Colunas (Garante compatibilidade total em updates)
            async with db.execute("PRAGMA table_info(users)") as cursor:
                existing_cols = [c[1] for c in await cursor.fetchall()]
                expected_cols = {
                    "role": "TEXT DEFAULT 'user'",
                    "status": "TEXT DEFAULT 'active'",
                    "tier": "TEXT DEFAULT 'unlimited'",
                    "selected_model": "TEXT DEFAULT 'deepseek'",
                    "custom_system_prompt": "TEXT",
                    "voice_mode_enabled": "INTEGER DEFAULT 0",
                    "daily_requests_count": "INTEGER DEFAULT 0",
                    "last_request_date": "TEXT",
                    "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                    "last_active_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
                }
                for col_name, col_def in expected_cols.items():
                    if col_name not in existing_cols:
                        logger.info(f"Auto-migrando coluna '{col_name}' na tabela 'users'...")
                        await db.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_def}")

            # Garante que o Admin Principal tenha role 'admin', status 'active' e tier 'unlimited'
            if settings.ADMIN_USER_ID:
                await db.execute(
                    """
                    INSERT INTO users (user_id, role, status, tier) VALUES (?, 'admin', 'active', 'unlimited')
                    ON CONFLICT(user_id) DO UPDATE SET role = 'admin', status = 'active', tier = 'unlimited'
                    """,
                    (settings.ADMIN_USER_ID,)
                )

            await db.commit()
            logger.info(f"Institutional Database initialized at {self.db_path}")

    # --- Operações de Autorização e Clientes ---

    async def is_user_authorized(self, user_id: int) -> bool:
        """Verifica se o usuário tem permissão para usar o bot de acordo com ACCESS_MODE."""
        if user_id == settings.ADMIN_USER_ID:
            return True

        if settings.ACCESS_MODE == "PRIVATE":
            return False

        async with self.get_connection() as db:
            async with db.execute("SELECT status FROM users WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return False
                status = row[0]
                if settings.ACCESS_MODE == "WHITELIST":
                    return status == "active"
                elif settings.ACCESS_MODE == "PUBLIC":
                    return status != "banned"
        return False

    async def request_user_access(self, user_id: int, username: str, first_name: str) -> dict:
        """Registra a solicitação de acesso de um novo cliente em status 'pending'."""
        today_str = str(date.today())
        async with self.get_connection() as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    await db.execute(
                        "UPDATE users SET username = ?, first_name = ?, last_active_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                        (username, first_name, user_id)
                    )
                    await db.commit()
                    return dict(row)

            await db.execute(
                """
                INSERT INTO users (user_id, username, first_name, role, status, tier, selected_model, last_request_date)
                VALUES (?, ?, ?, 'user', 'pending', 'free', ?, ?)
                """,
                (user_id, username, first_name, settings.DEFAULT_MODEL, today_str)
            )
            await db.commit()
            return {
                "user_id": user_id,
                "username": username,
                "first_name": first_name,
                "status": "pending",
                "tier": "free"
            }

    async def approve_user_access(self, user_id: int, tier: str = "free") -> dict:
        """Aprova o acesso de um cliente e define seu plano (free, pro, unlimited)."""
        async with self.get_connection() as db:
            await db.execute(
                "UPDATE users SET status = 'active', tier = ?, last_active_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                (tier, user_id)
            )
            await db.commit()
            return {"user_id": user_id, "status": "active", "tier": tier}

    async def check_and_increment_quota(self, user_id: int) -> tuple[bool, int, int, str]:
        """
        Verifica a cota diária do usuário.
        Retorna: (is_allowed, current_count, max_quota, tier)
        """
        if user_id == settings.ADMIN_USER_ID:
            return True, 0, 999999, "unlimited"

        today_str = str(date.today())
        async with self.get_connection() as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return False, 0, 0, "free"

                user = dict(row)
                tier = user.get("tier", "free")
                max_quota = settings.TIER_QUOTAS.get(tier, 30)

                current_count = user.get("daily_requests_count", 0)
                if user.get("last_request_date") != today_str:
                    current_count = 0
                    await db.execute(
                        "UPDATE users SET daily_requests_count = 1, last_request_date = ? WHERE user_id = ?",
                        (today_str, user_id)
                    )
                    await db.commit()
                    return True, 1, max_quota, tier

                if current_count >= max_quota:
                    return False, current_count, max_quota, tier

                await db.execute(
                    "UPDATE users SET daily_requests_count = daily_requests_count + 1 WHERE user_id = ?",
                    (user_id,)
                )
                await db.commit()
                return True, current_count + 1, max_quota, tier

    async def get_or_create_user(self, user_id: int, username: str = "", first_name: str = "") -> dict:
        today_str = str(date.today())
        async with self.get_connection() as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    user_dict = dict(row)
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

            role = "admin" if user_id == settings.ADMIN_USER_ID else "user"
            status = "active" if role == "admin" else ("active" if settings.ACCESS_MODE == "PUBLIC" else "pending")
            tier = "unlimited" if role == "admin" else "free"
            
            await db.execute(
                """
                INSERT INTO users (user_id, username, first_name, role, status, tier, selected_model, last_request_date, voice_mode_enabled)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
                """,
                (user_id, username, first_name, role, status, tier, settings.DEFAULT_MODEL, today_str)
            )
            await db.commit()
            return {
                "user_id": user_id,
                "username": username,
                "first_name": first_name,
                "role": role,
                "status": status,
                "tier": tier,
                "selected_model": settings.DEFAULT_MODEL,
                "custom_system_prompt": None,
                "voice_mode_enabled": 0,
                "daily_requests_count": 0,
                "last_request_date": today_str
            }

    async def update_user_model(self, user_id: int, model: str) -> None:
        async with self.get_connection() as db:
            await db.execute("UPDATE users SET selected_model = ? WHERE user_id = ?", (model, user_id))
            await db.commit()

    async def update_user_system_prompt(self, user_id: int, prompt: str | None) -> None:
        async with self.get_connection() as db:
            await db.execute("UPDATE users SET custom_system_prompt = ? WHERE user_id = ?", (prompt, user_id))
            await db.commit()

    async def toggle_voice_mode(self, user_id: int) -> bool:
        async with self.get_connection() as db:
            async with db.execute("SELECT voice_mode_enabled FROM users WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                current = row[0] if row and row[0] is not None else 0
                new_state = 1 if current == 0 else 0
            
            await db.execute("UPDATE users SET voice_mode_enabled = ? WHERE user_id = ?", (new_state, user_id))
            await db.commit()
            return bool(new_state)

    async def is_voice_mode_enabled(self, user_id: int) -> bool:
        async with self.get_connection() as db:
            async with db.execute("SELECT voice_mode_enabled FROM users WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                return bool(row[0]) if row and row[0] is not None else False

    async def set_user_status(self, user_id: int, status: str) -> None:
        async with self.get_connection() as db:
            await db.execute("UPDATE users SET status = ? WHERE user_id = ?", (status, user_id))
            await db.commit()

    async def set_user_tier(self, user_id: int, tier: str) -> None:
        async with self.get_connection() as db:
            await db.execute("UPDATE users SET tier = ? WHERE user_id = ?", (tier, user_id))
            await db.commit()

    # --- Memórias de Longo Prazo ---

    async def add_memory(self, user_id: int, memory_text: str) -> int:
        async with self.get_connection() as db:
            cursor = await db.execute(
                "INSERT INTO user_memories (user_id, memory_text) VALUES (?, ?)",
                (user_id, memory_text.strip())
            )
            await db.commit()
            return cursor.lastrowid

    async def get_memories(self, user_id: int) -> list[dict]:
        async with self.get_connection() as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT id, memory_text, created_at FROM user_memories WHERE user_id = ? ORDER BY id ASC",
                (user_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def delete_memory(self, memory_id: int, user_id: int) -> bool:
        async with self.get_connection() as db:
            cursor = await db.execute(
                "DELETE FROM user_memories WHERE id = ? AND user_id = ?",
                (memory_id, user_id)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def clear_memories(self, user_id: int) -> None:
        async with self.get_connection() as db:
            await db.execute("DELETE FROM user_memories WHERE user_id = ?", (user_id,))
            await db.commit()

    # --- Mensagens e Histórico ---

    async def save_message(self, user_id: int, role: str, content: str, model_used: str = "") -> None:
        async with self.get_connection() as db:
            await db.execute(
                "INSERT INTO messages (user_id, role, content, model_used) VALUES (?, ?, ?, ?)",
                (user_id, role, content, model_used)
            )
            await db.commit()

    async def get_context_history(self, user_id: int, limit: int = settings.MAX_CONTEXT_TURNS) -> list[dict]:
        async with self.get_connection() as db:
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

    async def get_full_conversation_history(self, user_id: int) -> list[dict]:
        async with self.get_connection() as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT id, role, content, model_used, created_at FROM messages WHERE user_id = ? ORDER BY id ASC",
                (user_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def clear_history(self, user_id: int) -> None:
        async with self.get_connection() as db:
            await db.execute("DELETE FROM messages WHERE user_id = ?", (user_id,))
            await db.commit()

    # --- Métricas e Administração ---

    async def record_usage(self, user_id: int, action_type: str, model: str = "") -> None:
        async with self.get_connection() as db:
            await db.execute(
                "INSERT INTO usage_metrics (user_id, action_type, model) VALUES (?, ?, ?)",
                (user_id, action_type, model)
            )
            await db.commit()

    async def get_admin_dashboard_stats(self) -> dict:
        async with self.get_connection() as db:
            async with db.execute("SELECT COUNT(*) FROM users") as c1:
                total_users = (await c1.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM users WHERE status = 'active'") as c2:
                active_users = (await c2.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM users WHERE status = 'pending'") as cp:
                pending_users = (await cp.fetchone())[0]
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
                "pending_users": pending_users,
                "pro_users": pro_users,
                "total_messages": total_messages,
                "messages_today": messages_today,
                "images_gen": images_gen,
                "web_searches": web_searches
            }

    async def get_all_users_for_broadcast(self) -> list[int]:
        async with self.get_connection() as db:
            async with db.execute("SELECT user_id FROM users WHERE status = 'active'") as cursor:
                rows = await cursor.fetchall()
                return [r[0] for r in rows]

    async def get_top_users(self, limit: int = 10) -> list[dict]:
        async with self.get_connection() as db:
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
        async with self.get_connection() as db:
            async with db.execute("SELECT value FROM system_settings WHERE key = ?", (key,)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else default

    async def set_system_setting(self, key: str, value: str) -> None:
        async with self.get_connection() as db:
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
