"""
Institutional Resilience, Circuit Breakers, Rate Limiting, and Telemetry Engine.
"""
import asyncio
from datetime import datetime, timedelta
import logging
import os
import time
import psutil
from app.config import settings

logger = logging.getLogger(__name__)

class CircuitBreaker:
    """Proteção inteligente contra quedas e falhas em APIs de IA."""
    def __init__(self, failure_threshold: int = 3, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_counts: dict[str, int] = {}
        self.last_failure_time: dict[str, float] = {}
        self.circuit_state: dict[str, str] = {}  # 'CLOSED', 'OPEN', 'HALF-OPEN'

    def is_available(self, provider_key: str) -> bool:
        state = self.circuit_state.get(provider_key, "CLOSED")
        if state == "CLOSED":
            return True
        elif state == "OPEN":
            last_fail = self.last_failure_time.get(provider_key, 0)
            if time.time() - last_fail > self.recovery_timeout:
                self.circuit_state[provider_key] = "HALF-OPEN"
                logger.info(f"Circuit Breaker para '{provider_key}' mudou para HALF-OPEN (testando recuperação).")
                return True
            return False
        elif state == "HALF-OPEN":
            return True
        return True

    def record_success(self, provider_key: str):
        self.failure_counts[provider_key] = 0
        self.circuit_state[provider_key] = "CLOSED"

    def record_failure(self, provider_key: str):
        count = self.failure_counts.get(provider_key, 0) + 1
        self.failure_counts[provider_key] = count
        self.last_failure_time[provider_key] = time.time()
        
        if count >= self.failure_threshold:
            self.circuit_state[provider_key] = "OPEN"
            logger.warning(f"🚨 Circuit Breaker ABERTO para '{provider_key}' após {count} falhas consecutivas.")

circuit_breaker = CircuitBreaker()

class SystemTelemetry:
    """Coletor de telemetria e integridade do servidor em tempo real."""
    START_TIME = time.time()

    @staticmethod
    def get_metrics() -> dict:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        uptime_seconds = int(time.time() - SystemTelemetry.START_TIME)
        
        uptime_str = str(timedelta(seconds=uptime_seconds))

        db_size_mb = 0.0
        if settings.DATABASE_PATH.exists():
            db_size_mb = settings.DATABASE_PATH.stat().st_size / (1024 * 1024)

        return {
            "cpu_percent": cpu_percent,
            "ram_used_mb": ram.used / (1024 * 1024),
            "ram_total_mb": ram.total / (1024 * 1024),
            "ram_percent": ram.percent,
            "disk_used_gb": disk.used / (1024 * 1024 * 1024),
            "disk_total_gb": disk.total / (1024 * 1024 * 1024),
            "disk_percent": disk.percent,
            "uptime": uptime_str,
            "db_size_mb": round(db_size_mb, 2)
        }

telemetry = SystemTelemetry()
