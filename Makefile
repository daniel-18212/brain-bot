.PHONY: help install run-dev build up down logs clean docker-build

help:
	@echo "Comandos disponíveis:"
	@echo "  make install    - Instala dependências no ambiente virtual"
	@echo "  make run-dev    - Executa o bot localmente em modo desenvolvimento"
	@echo "  make build      - Constrói a imagem Docker"
	@echo "  make up         - Inicia o container Docker em segundo plano"
	@echo "  make down       - Para o container Docker"
	@echo "  make logs       - Visualiza logs do container Docker em tempo real"
	@echo "  make clean      - Remove arquivos temporários e caches"

install:
	python3 -m pip install --upgrade pip
	pip install -r requirements.txt

run-dev:
	python3 -m app.main

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
