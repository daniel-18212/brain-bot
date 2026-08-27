# =====================================================================
# Institutional Production Dockerfile with Astral UV
# =====================================================================
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    UV_SYSTEM_PYTHON=1 \
    HEALTH_PORT=8080

# Instalação do UV e resolução ultrarrápida de dependências
RUN pip install --no-cache-dir uv

COPY pyproject.toml .
RUN uv pip install -r pyproject.toml --system

# Cria usuário não-root por segurança e conformidade
RUN groupadd -g 1000 appgroup && \
    useradd -u 1000 -g appgroup -m -s /bin/bash appuser && \
    mkdir -p /app/data && \
    chown -R appuser:appgroup /app

COPY --chown=appuser:appgroup . /app

USER appuser

EXPOSE 8080
VOLUME ["/app/data"]

CMD ["python", "-m", "app.main"]
