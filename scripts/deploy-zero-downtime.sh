#!/bin/bash
# Zero-Downtime Deployment Script for Proxi (Linux)
# Strategy: Build first, then quick restart with health check wait
#
# Usage: ./deploy-zero-downtime.sh [service]
# Example: ./deploy-zero-downtime.sh core
#          ./deploy-zero-downtime.sh frontend
#          ./deploy-zero-downtime.sh all

set -e
cd "$(dirname "$0")/.."

SERVICE="${1:-all}"

echo -e "\n\033[36m=== Zero-Downtime Deploy: $SERVICE ===\033[0m"

wait_for_health() {
    local url=$1
    local max_wait=${2:-60}
    local attempts=0
    
    while [ $attempts -lt $max_wait ]; do
        if curl -sf "$url" > /dev/null 2>&1; then
            return 0
        fi
        sleep 1
        attempts=$((attempts + 1))
        echo -n "."
    done
    return 1
}

deploy_service() {
    local svc=$1
    local health_url=$2
    
    echo -e "\n\033[33m[$svc] Building new image (app stays up during build)...\033[0m"
    docker-compose build "$svc"
    
    echo -e "\033[33m[$svc] Quick restart with new image...\033[0m"
    docker-compose up -d --no-deps --force-recreate "$svc"
    
    echo -n -e "\033[33m[$svc] Waiting for health \033[0m"
    if wait_for_health "$health_url"; then
        echo ""
        echo -e "\033[32m[$svc] Deployed successfully!\033[0m"
    else
        echo ""
        echo -e "\033[31m[$svc] WARNING: Health check timed out, check logs\033[0m"
        docker-compose logs --tail 20 "$svc"
    fi
}

# Pull latest code first (no downtime)
echo -e "\n\033[33mPulling latest code...\033[0m"
git pull

declare -A services=(
    ["core"]="http://localhost:4000/health"
    ["frontend"]="http://localhost:4002"
)

case "$SERVICE" in
    all)
        deploy_service "core" "${services[core]}"
        deploy_service "frontend" "${services[frontend]}"
        ;;
    core|frontend)
        deploy_service "$SERVICE" "${services[$SERVICE]}"
        ;;
    *)
        echo -e "\033[31mUnknown service: $SERVICE. Use: core, frontend, or all\033[0m"
        exit 1
        ;;
esac

echo -e "\n\033[32m=== Deployment Complete ===\033[0m"
docker-compose ps
