#!/bin/bash

# =============================================================================
# Proxi Linux Agent Deployment Script
# =============================================================================
# Target: Docker container running on Oracle Ubuntu frontend server
# Base: Alpine Linux (lightweight, ~5MB base image)
# Purpose: Always-on backend for terminal, git, python, file operations
#
# Usage: ./deploy-linux-agent.sh
# Prerequisites: Docker installed on host
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CONTAINER_NAME="proxi-linux-agent"
IMAGE_NAME="proxi-linux-agent:latest"
AGENT_PORT=8081

echo "========================================"
echo "   🐧 PROXI LINUX AGENT DEPLOYMENT"
echo "========================================"

# -----------------------------------------------------------------------------
# 1. Check Docker
# -----------------------------------------------------------------------------
echo "[1/6] Checking Docker..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker first."
    echo "   Run: curl -fsSL https://get.docker.com | sh"
    exit 1
fi
echo "   ✅ Docker available"

# -----------------------------------------------------------------------------
# 2. Create Dockerfile for Linux Agent
# -----------------------------------------------------------------------------
echo "[2/6] Creating Linux Agent Dockerfile..."

DOCKERFILE_PATH="$PROJECT_ROOT/docker/linux-agent/Dockerfile"
mkdir -p "$(dirname "$DOCKERFILE_PATH")"

cat > "$DOCKERFILE_PATH" << 'DOCKERFILE'
# =============================================================================
# Proxi Linux Agent - Alpine-based lightweight container
# =============================================================================
FROM python:3.12-alpine

# Install essential tools
RUN apk add --no-cache \
    git \
    curl \
    bash \
    openssh-client \
    docker-cli \
    jq \
    htop \
    vim \
    && rm -rf /var/cache/apk/*

# Create app directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend /app/backend

# Create workspace directory for file operations
RUN mkdir -p /workspace && chmod 777 /workspace

# Environment
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV AGENT_TYPE=linux-container
ENV WORKSPACE_DIR=/workspace

# Expose agent port
EXPOSE 8081

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8081/health || exit 1

# Start the agent
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8081"]
DOCKERFILE

echo "   ✅ Dockerfile created at $DOCKERFILE_PATH"

# -----------------------------------------------------------------------------
# 3. Create docker compose for Linux Agent
# -----------------------------------------------------------------------------
echo "[3/6] Creating docker compose configuration..."

COMPOSE_PATH="$PROJECT_ROOT/docker/linux-agent/docker compose.yml"

cat > "$COMPOSE_PATH" << 'COMPOSE'
version: '3.8'

services:
  linux-agent:
    build:
      context: ../..
      dockerfile: docker/linux-agent/Dockerfile
    image: proxi-linux-agent:latest
    container_name: proxi-linux-agent
    restart: unless-stopped
    ports:
      - "8081:8081"
    volumes:
      # Workspace for file operations
      - proxi-workspace:/workspace
      # Optional: mount host docker socket for docker-in-docker
      - /var/run/docker.sock:/var/run/docker.sock:ro
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - AGENT_TYPE=linux-container
      - WORKSPACE_DIR=/workspace
    env_file:
      - ../../.env
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8081/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    networks:
      - proxi-network

volumes:
  proxi-workspace:
    driver: local

networks:
  proxi-network:
    driver: bridge
COMPOSE

echo "   ✅ docker compose.yml created at $COMPOSE_PATH"

# -----------------------------------------------------------------------------
# 4. Check for .env file
# -----------------------------------------------------------------------------
echo "[4/6] Checking environment configuration..."

if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo "   ⚠️  No .env file found. Creating template..."
    cat > "$PROJECT_ROOT/.env" << 'ENVFILE'
# Proxi Environment Configuration
GEMINI_API_KEY=your_api_key_here
GITHUB_TOKEN=optional_github_token

# Agent Configuration
AGENT_TYPE=linux-container
WORKSPACE_DIR=/workspace
ENVFILE
    echo "   ⚠️  Please edit .env with your GEMINI_API_KEY!"
else
    echo "   ✅ .env file exists"
fi

# -----------------------------------------------------------------------------
# 5. Build and Start Container
# -----------------------------------------------------------------------------
echo "[5/6] Building and starting Linux Agent..."

cd "$PROJECT_ROOT/docker/linux-agent"

# Stop existing container if running
docker stop $CONTAINER_NAME 2>/dev/null || true
docker rm $CONTAINER_NAME 2>/dev/null || true

# Build and start
docker compose up -d --build

echo "   ✅ Container started"

# -----------------------------------------------------------------------------
# 6. Verify Deployment
# -----------------------------------------------------------------------------
echo "[6/6] Verifying deployment..."

sleep 5

if curl -s http://localhost:$AGENT_PORT/health > /dev/null 2>&1; then
    echo "   ✅ Linux Agent is healthy at http://localhost:$AGENT_PORT"
else
    echo "   ⚠️  Agent may still be starting. Check logs with:"
    echo "      docker logs $CONTAINER_NAME"
fi

echo ""
echo "========================================"
echo "   ✅ Linux Agent Deployment Complete!"
echo "========================================"
echo ""
echo "   Agent URL: http://localhost:$AGENT_PORT"
echo "   Health:    http://localhost:$AGENT_PORT/health"
echo ""
echo "   Commands:"
echo "   - Logs:    docker logs -f $CONTAINER_NAME"
echo "   - Shell:   docker exec -it $CONTAINER_NAME /bin/bash"
echo "   - Stop:    docker stop $CONTAINER_NAME"
echo "   - Restart: docker restart $CONTAINER_NAME"
echo ""
echo "========================================"
