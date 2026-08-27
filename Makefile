.PHONY: help install run-dev build up down restart logs health clean test

help:
	@echo "Comandos disponíveis (Baseados em Astral UV & Docker):"
	@echo "  make install    - Instala todas as dependências ultrarrápido com UV"
	@echo "  make run-dev    - Executa o bot localmente em modo desenvolvimento"
	@echo "  make build      - Constrói a imagem Docker de produção otimizada com UV"
	@echo "  make up         - Inicia o container Docker em segundo plano (24/7)"
	@echo "  make down       - Para o container Docker com desligamento seguro"
	@echo "  make restart    - Reinicia o container Docker"
	@echo "  make logs       - Visualiza os logs em tempo real do container"
	@echo "  make health     - Testa o endpoint HTTP /health do bot"
	@echo "  make clean      - Remove caches e arquivos temporários"

install:
	uv venv && uv pip install -r pyproject.toml

run-dev:
	uv run python -m app.main

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

restart:
	docker compose restart

logs:
	docker compose logs -f

health:
	curl -s http://localhost:8080/health | python3 -m json.tool

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
