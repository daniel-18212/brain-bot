# =====================================================================
# Enterprise Production Dockerfile for BrainBot (Instant Build)
# =====================================================================
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Cria usuário não-root por segurança
RUN groupadd -g 1000 appgroup && \
    useradd -u 1000 -g appgroup -m -s /bin/bash appuser && \
    mkdir -p /app/data && \
    chown -R appuser:appgroup /app

COPY --chown=appuser:appgroup . /app

USER appuser

VOLUME ["/app/data"]

CMD ["python", "-m", "app.main"]
