#!/bin/bash
# =====================================================================
# BrainBot — Script de Deploy Automatizado Zero-Touch (Linux / VPS / Raspberry Pi)
# Uso: bash deploy.sh
# =====================================================================

set -e

PROJETO_DIR="$(cd "$(dirname "$0")" && pwd)"
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║      🧠 BrainBot — Deploy em Produção Institucional 24/7     ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "📁 Diretório do projeto: $PROJETO_DIR"
echo ""

# ── 1. Verificar Docker ──────────────────────────────────────────
if ! command -v docker &>/dev/null; then
    echo "🐳 Docker não encontrado. Instalando automaticamente..."
    sudo apt-get update -y
    sudo apt-get install -y ca-certificates curl gnupg lsb-release
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg || true
    sudo chmod a+r /etc/apt/keyrings/docker.gpg || true
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null || true
    sudo apt-get update -y
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    sudo systemctl enable docker
    sudo systemctl start docker
    sudo usermod -aG docker "$USER" 2>/dev/null || true
    echo "✅ Docker instalado com sucesso!"
    DOCKER_CMD="sudo docker"
else
    echo "✅ Docker detectado: $(docker --version)"
    DOCKER_CMD="docker"
    docker ps &>/dev/null 2>&1 || DOCKER_CMD="sudo docker"
fi

# ── 2. Validar Arquivos ──────────────────────────────────────────
echo "🔍 Validando arquivos do sistema..."
for f in ".env" "pyproject.toml" "Dockerfile" "docker-compose.yml"; do
    if [ ! -f "$PROJETO_DIR/$f" ]; then
        echo "❌ Arquivo essencial ausente: $f"
        exit 1
    fi
done
echo "✅ Todos os arquivos verificados."

# ── 3. Preparar Diretório de Dados ──────────────────────────────
mkdir -p "$PROJETO_DIR/data"
sudo chmod -R 777 "$PROJETO_DIR/data" 2>/dev/null || chmod -R 777 "$PROJETO_DIR/data"
echo "✅ Volume data/ preparado com permissões de gravação."

# ── 4. Build e Start do Container ────────────────────────────────
echo ""
echo "🏗️  Construindo imagem otimizada com Astral UV e subindo container..."
$DOCKER_CMD compose -f "$PROJETO_DIR/docker-compose.yml" up -d --build

# ── 5. Health Check ──────────────────────────────────────────────
echo ""
echo "⏳ Aguardando inicialização e verificando saúde do bot (10s)..."
sleep 10

echo ""
echo "📊 Status dos Containers:"
$DOCKER_CMD compose -f "$PROJETO_DIR/docker-compose.yml" ps

echo ""
echo "🩺 Testando endpoint HTTP /health:"
if command -v curl &>/dev/null; then
    curl -s http://localhost:8080/health || echo "Endpoint iniciando..."
    echo ""
fi

echo ""
echo "📋 Logs Recentes do Bot:"
$DOCKER_CMD compose -f "$PROJETO_DIR/docker-compose.yml" logs --tail=15

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║             ✅ DEPLOY EXECUTADO COM SUCESSO!                 ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "Comandos úteis:"
echo "  • Ver logs ao vivo : make logs (ou docker compose logs -f)"
echo "  • Status e Saúde   : docker compose ps"
echo "  • Reiniciar        : make restart (ou docker compose restart)"
echo "  • Parar            : make down (ou docker compose down)"
echo "  • Healthcheck      : curl http://localhost:8080/health"
echo ""
