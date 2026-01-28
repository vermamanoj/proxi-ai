#!/bin/bash

# Master Deployment Script for Proxi
# 
# Usage: 
#   ./deploy.sh              # Full deployment (pull + docker + nginx)
#   ./deploy.sh --docker     # Rebuild Docker containers only
#   ./deploy.sh --nginx      # Update nginx config and reload
#   ./deploy.sh --pull       # Git pull only
#   ./deploy.sh --logs       # View container logs
#   ./deploy.sh --status     # Check service status
#   ./deploy.sh --restart    # Restart containers without rebuild
#
# Prerequisites:
#   - Docker and Docker Compose installed
#   - .env file configured with GEMINI_API_KEY
#   - Nginx installed (for production with SSL)

set -e  # Exit immediately if a command exits with a non-zero status.

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
NGINX_CONF_SRC="./deploy/proxi.conf"
NGINX_AVAIL="/etc/nginx/sites-available/proxi"
NGINX_ENABLED="/etc/nginx/sites-enabled/proxi"

# ============================================================
# Helper Functions
# ============================================================

show_help() {
    echo -e "${CYAN}Proxi Deployment Script${NC}"
    echo ""
    echo "Usage: ./deploy.sh [OPTION]"
    echo ""
    echo "Options:"
    echo "  (no option)    Full deployment (pull + docker + nginx)"
    echo "  --docker       Rebuild and restart Docker containers"
    echo "  --nginx        Update nginx config and reload"
    echo "  --pull         Git pull latest code"
    echo "  --logs         View container logs (follow mode)"
    echo "  --status       Check service status"
    echo "  --restart      Restart containers without rebuild"
    echo "  --help         Show this help message"
    echo ""
}

do_pull() {
    echo -e "${CYAN}[GIT] Pulling latest changes...${NC}"
    if [ -d ".git" ]; then
        git pull origin main || echo -e "${YELLOW}   Skipping git pull (may not have remote)${NC}"
    else
        echo -e "${YELLOW}   Not a git repository${NC}"
    fi
}

do_docker() {
    echo -e "${CYAN}[DOCKER] Building and starting containers...${NC}"
    
    # Check for .env file
    if [ ! -f ".env" ]; then
        echo -e "${YELLOW}⚠️  Warning: .env file not found.${NC}"
        if [ -f ".env.example" ]; then
            echo "   Creating .env from .env.example..."
            cp .env.example .env
            echo -e "${YELLOW}   ⚠️  Please edit .env with your API keys!${NC}"
        else
            echo -e "${RED}❌ Error: No .env or .env.example found.${NC}"
            exit 1
        fi
    fi
    
    # Check for Docker
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Error: Docker is not installed.${NC}"
        exit 1
    fi
    
    docker compose down --remove-orphans 2>/dev/null || true
    docker compose up -d --build
    
    echo -e "${CYAN}[DOCKER] Waiting for services to start...${NC}"
    sleep 5
    
    # Check health
    if curl -s http://localhost:4000/api/health > /dev/null 2>&1; then
        echo -e "${GREEN}   ✅ Backend is responding${NC}"
    else
        echo -e "${YELLOW}   ⚠️  Backend may still be starting...${NC}"
    fi
    
    if curl -s http://localhost:4001/health > /dev/null 2>&1; then
        echo -e "${GREEN}   ✅ Agent is responding${NC}"
    fi
}

do_nginx() {
    echo -e "${CYAN}[NGINX] Updating configuration...${NC}"
    
    if [ ! -f "$NGINX_CONF_SRC" ]; then
        echo -e "${RED}❌ Error: $NGINX_CONF_SRC not found${NC}"
        exit 1
    fi
    
    if ! command -v nginx &> /dev/null; then
        echo -e "${RED}❌ Error: Nginx is not installed${NC}"
        exit 1
    fi
    
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
    if sudo nginx -t; then
        echo "   -> Reloading Nginx service..."
        sudo systemctl reload nginx
        echo -e "${GREEN}   ✅ Nginx configured and reloaded${NC}"
    else
        echo -e "${RED}   ❌ Nginx config test failed!${NC}"
        exit 1
    fi
}

do_restart() {
    echo -e "${CYAN}[DOCKER] Restarting containers...${NC}"
    docker compose restart
    echo -e "${GREEN}   ✅ Containers restarted${NC}"
}

do_logs() {
    echo -e "${CYAN}[LOGS] Following container logs (Ctrl+C to exit)...${NC}"
    docker compose logs -f
}

do_status() {
    echo -e "${CYAN}========================================"
    echo "   PROXI SERVICE STATUS"
    echo "========================================${NC}"
    echo ""
    
    echo -e "${CYAN}[Docker Containers]${NC}"
    docker compose ps
    echo ""
    
    echo -e "${CYAN}[Health Checks]${NC}"
    
    # Backend
    if curl -s http://localhost:4000/api/health > /dev/null 2>&1; then
        echo -e "   Core (4000):     ${GREEN}✅ Online${NC}"
    else
        echo -e "   Core (4000):     ${RED}❌ Offline${NC}"
    fi
    
    # Agent
    if curl -s http://localhost:4001/health > /dev/null 2>&1; then
        echo -e "   Agent (4001):    ${GREEN}✅ Online${NC}"
    else
        echo -e "   Agent (4001):    ${RED}❌ Offline${NC}"
    fi
    
    # Frontend
    if curl -s http://localhost:4002 > /dev/null 2>&1; then
        echo -e "   Frontend (4002): ${GREEN}✅ Online${NC}"
    else
        echo -e "   Frontend (4002): ${RED}❌ Offline${NC}"
    fi
    
    # Nginx
    echo ""
    echo -e "${CYAN}[Nginx]${NC}"
    if systemctl is-active --quiet nginx; then
        echo -e "   Status: ${GREEN}✅ Running${NC}"
    else
        echo -e "   Status: ${RED}❌ Not running${NC}"
    fi
}

do_full_deploy() {
    echo -e "${CYAN}========================================"
    echo "   🚀 PROXI FULL DEPLOYMENT"
    echo "========================================${NC}"
    echo ""
    
    do_pull
    echo ""
    do_docker
    echo ""
    do_nginx
    
    echo ""
    echo -e "${GREEN}========================================"
    echo "   ✅ Deployment Complete!"
    echo "========================================${NC}"
    echo ""
    echo "   Services:"
    echo "   - Frontend: https://proxi.audista.com"
    echo "   - Core API: http://localhost:4000"
    echo "   - Agent:    http://localhost:4001"
    echo ""
    echo "   Commands:"
    echo "   - Logs:    ./deploy.sh --logs"
    echo "   - Status:  ./deploy.sh --status"
    echo "   - Restart: ./deploy.sh --restart"
    echo "========================================"
}

# ============================================================
# Main
# ============================================================

case "${1:-}" in
    --help|-h)
        show_help
        ;;
    --docker)
        do_docker
        ;;
    --nginx)
        do_nginx
        ;;
    --pull)
        do_pull
        ;;
    --logs)
        do_logs
        ;;
    --status)
        do_status
        ;;
    --restart)
        do_restart
        ;;
    "")
        do_full_deploy
        ;;
    *)
        echo -e "${RED}Unknown option: $1${NC}"
        show_help
        exit 1
        ;;
esac
