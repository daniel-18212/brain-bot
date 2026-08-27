"""
Asynchronous HTTP Health Check Server for Docker & External Monitoring.
Runs on Port 8080 (or HEALTH_PORT).
"""
import asyncio
import logging
import time
from aiohttp import web
from app.config import settings
from app.core.resilience import telemetry
from app.database import db

logger = logging.getLogger(__name__)

async def health_handler(request: web.Request) -> web.Response:
    """Retorna estado do bot, métricas de hardware e integridade do banco."""
    m = telemetry.get_metrics()
    
    # Testa integridade do banco SQLite
    db_ok = True
    try:
        async with db.get_connection() as conn:
            async with conn.execute("SELECT 1") as cursor:
                await cursor.fetchone()
    except Exception as e:
        logger.error(f"Healthcheck: Falha ao consultar SQLite: {e}")
        db_ok = False

    status_str = "ok" if db_ok else "degraded"

    payload = {
        "status": status_str,
        "bot": "online",
        "access_mode": settings.ACCESS_MODE,
        "default_model": settings.DEFAULT_MODEL,
        "database": "healthy" if db_ok else "error",
        "cpu_percent": m["cpu_percent"],
        "ram_used_mb": round(m["ram_used_mb"], 1),
        "disk_used_gb": round(m["disk_used_gb"], 1),
        "db_size_mb": m["db_size_mb"],
        "uptime": m["uptime"],
        "timestamp": int(time.time())
    }

    status_code = 200 if db_ok else 503
    return web.json_response(payload, status=status_code)

async def start_health_server(host: str = "0.0.0.0", port: int = 8080) -> web.AppRunner:
    """Inicia o servidor web leve do healthcheck."""
    app = web.Application()
    app.router.add_get("/health", health_handler)
    app.router.add_get("/", health_handler)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    logger.info(f"🩺 Servidor HTTP de Health Check ativo em http://{host}:{port}/health")
    return runner
