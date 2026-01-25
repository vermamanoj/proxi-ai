#!/bin/bash

# Master Deployment Script for Proxi
# Usage: ./deploy.sh
#
# Prerequisites:
#   - Docker and Docker Compose installed
#   - .env file configured with GEMINI_API_KEY
#   - Nginx installed (for production with SSL)

set -e  # Exit immediately if a command exits with a non-zero status.

echo "========================================"
echo "   🚀 PROXI PRODUCTION DEPLOYMENT"
echo "========================================"

# Check for .env file
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found."
    if [ -f ".env.example" ]; then
        echo "   Creating .env from .env.example..."
        cp .env.example .env
        echo "   ⚠️  Please edit .env with your API keys!"
    else
        echo "❌ Error: No .env or .env.example found."
        exit 1
    fi
fi

# Check for Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed."
    echo "👉 Install Docker: https://docs.docker.com/engine/install/"
    exit 1
fi

# Check for Docker Compose
if ! docker compose version &> /dev/null; then
    echo "❌ Error: Docker Compose is not installed."
    echo "👉 Install Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

# 1. Pull latest code (optional, skip if not a git repo)
if [ -d ".git" ]; then
    echo "[1/4] Pulling latest changes from git..."
    git pull origin main || echo "   Skipping git pull (may not have remote)"
else
    echo "[1/4] Skipping git pull (not a git repository)"
fi

# 2. Rebuild and restart containers
echo "[2/4] Building and starting Docker containers..."
docker compose down --remove-orphans 2>/dev/null || true
docker compose up -d --build

# 3. Wait for services to be ready
echo "[3/4] Waiting for services to start..."
sleep 5

# Check if backend is responding
if curl -s http://localhost:4000/api/missions > /dev/null 2>&1; then
    echo "   ✅ Backend is responding"
else
    echo "   ⚠️  Backend may still be starting..."
fi

# 4. Sync Nginx Infrastructure (optional)
echo "[4/4] Configuring Nginx (if available)..."

NGINX_CONF_SRC="./deploy/proxi.conf"
NGINX_AVAIL="/etc/nginx/sites-available/proxi"
NGINX_ENABLED="/etc/nginx/sites-enabled/proxi"

if [ -f "$NGINX_CONF_SRC" ] && command -v nginx &> /dev/null; then
    # Copy config
    echo "   -> Copying configuration to $NGINX_AVAIL"
    sudo cp "$NGINX_CONF_SRC" "$NGINX_AVAIL"

    # Link if not exists
    if [ ! -L "$NGINX_ENABLED" ]; then
        echo "   -> Creating symlink to $NGINX_ENABLED"
        sudo ln -s "$NGINX_AVAIL" "$NGINX_ENABLED"
    fi

    # Test Nginx
    echo "   -> Testing Nginx configuration..."
    sudo nginx -t

    # Reload
    echo "   -> Reloading Nginx service..."
    sudo systemctl reload nginx
    echo "   ✅ Nginx configured"
else
    echo "   ⚠️  Skipping Nginx (not found or config missing)"
    echo "   Access directly at:"
    echo "   - Frontend: http://localhost:4001"
    echo "   - Backend:  http://localhost:4000"
fi

echo ""
echo "========================================"
echo "   ✅ Deployment Complete!"
echo "========================================"
echo ""
echo "   Services:"
echo "   - Frontend: http://localhost:4001"
echo "   - Backend:  http://localhost:4000"
echo ""
echo "   Logs: docker compose logs -f"
echo "   Stop: docker compose down"
echo "========================================"
