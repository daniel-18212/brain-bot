# =====================================================================
# Institutional Production Dockerfile with Astral UV (Ultra-Fast)
# =====================================================================
FROM ghcr.io/astral-sh/uv:latest AS uv_bin
FROM python:3.12-slim

WORKDIR /app

# Copia o binário UV do stage oficial
COPY --from=uv_bin /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    UV_SYSTEM_PYTHON=1

# Instalação ultrarrápida de dependências compiladas com UV
COPY pyproject.toml .
RUN uv pip install -r pyproject.toml --system

# Cria usuário não-root por segurança e conformidade
RUN groupadd -g 1000 appgroup && \
    useradd -u 1000 -g appgroup -m -s /bin/bash appuser && \
    mkdir -p /app/data && \
    chown -R appuser:appgroup /app

COPY --chown=appuser:appgroup . /app

USER appuser

VOLUME ["/app/data"]

CMD ["python", "-m", "app.main"]
