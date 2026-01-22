#!/bin/bash

# Master Deployment Script for Proxi
# Usage: ./deploy.sh

set -e # Exit immediately if a command exits with a non-zero status.

echo "========================================"
echo "   🚀 PROXI PRODUCTION DEPLOYMENT"
echo "========================================"

# 1. Pull latest code
echo "[1/4] Pulling latest changes from git..."
git pull origin main

# 2. Rebuild and restart containers
echo "[2/4] Updating Docker containers..."
docker compose up -d --build

# 3. Sync Nginx Infrastructure
echo "[3/4] Configuring Nginx..."

NGINX_CONF_SRC="./deploy/proxi.conf"
NGINX_AVAIL="/etc/nginx/sites-available/proxi"
NGINX_ENABLED="/etc/nginx/sites-enabled/proxi"

if [ -f "$NGINX_CONF_SRC" ]; then
    # Copy config
    echo " -> Copying configuration to $NGINX_AVAIL"
    sudo cp "$NGINX_CONF_SRC" "$NGINX_AVAIL"

    # Link if not exists
    if [ ! -L "$NGINX_ENABLED" ]; then
        echo " -> Creating symlink to $NGINX_ENABLED"
        sudo ln -s "$NGINX_AVAIL" "$NGINX_ENABLED"
    fi

    # Test Nginx
    echo " -> Testing Nginx configuration..."
    sudo nginx -t

    # Reload
    echo " -> Reloading Nginx service..."
    sudo systemctl reload nginx
else
    echo "❌ Error: Nginx config file not found at $NGINX_CONF_SRC"
    exit 1
fi

echo "========================================"
echo "   ✅ Deployment Complete."
echo "========================================"
