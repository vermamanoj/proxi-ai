#!/bin/bash
# Deploy Proxi to Linux server (proxi.audista.com)
# Usage: ./deploy-linux.sh [--build] [--ssl]

set -e

echo "=========================================="
echo "  PROXI DEPLOYMENT - Linux Server"
echo "=========================================="

BUILD_FLAG=""
SSL_SETUP=false

# Parse arguments
for arg in "$@"; do
    case $arg in
        --build)
            BUILD_FLAG="--build"
            ;;
        --ssl)
            SSL_SETUP=true
            ;;
    esac
done

# Check .env file exists
if [ ! -f .env ]; then
    echo "ERROR: .env file not found!"
    echo "Create .env with GEMINI_API_KEY=your-key"
    exit 1
fi

# Check GEMINI_API_KEY is set
if ! grep -q "GEMINI_API_KEY=" .env; then
    echo "ERROR: GEMINI_API_KEY not found in .env"
    exit 1
fi

echo "[1/5] Checking Docker..."
docker --version || { echo "Docker not installed!"; exit 1; }
docker compose --version || docker compose version || { echo "Docker Compose not installed!"; exit 1; }

echo "[2/5] Creating data directories..."
mkdir -p data
mkdir -p nginx

echo "[3/5] Building and starting containers..."
docker compose up -d $BUILD_FLAG

echo "[4/5] Waiting for services to start..."
sleep 10

# Health checks
echo "[5/5] Running health checks..."

CORE_HEALTH=$(curl -s http://localhost:4000/api/health || echo "FAILED")
if echo "$CORE_HEALTH" | grep -q "online"; then
    echo "  ✓ Core: HEALTHY"
else
    echo "  ✗ Core: FAILED - $CORE_HEALTH"
fi

AGENT_HEALTH=$(curl -s http://localhost:4001/health || echo "FAILED")
if echo "$AGENT_HEALTH" | grep -q "healthy"; then
    echo "  ✓ Agent: HEALTHY"
else
    echo "  ✗ Agent: FAILED - $AGENT_HEALTH"
fi

FRONTEND=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:4002 || echo "000")
if [ "$FRONTEND" = "200" ]; then
    echo "  ✓ Frontend: HEALTHY"
else
    echo "  ✗ Frontend: HTTP $FRONTEND"
fi

echo ""
echo "=========================================="
echo "  DEPLOYMENT COMPLETE"
echo "=========================================="
echo ""
echo "Services running:"
echo "  - Frontend: http://localhost:4002"
echo "  - Core API: http://localhost:4000"
echo "  - Agent:    http://localhost:4001"
echo ""

if [ "$SSL_SETUP" = true ]; then
    echo "Setting up SSL with Let's Encrypt..."
    docker run -it --rm \
        -v /etc/letsencrypt:/etc/letsencrypt \
        -v /var/lib/letsencrypt:/var/lib/letsencrypt \
        -p 80:80 \
        certbot/certbot certonly --standalone \
        -d proxi.audista.com \
        --email admin@audista.com \
        --agree-tos --no-eff-email
    echo "SSL certificate installed. Update nginx.conf to enable HTTPS."
fi

echo "To view logs: docker compose logs -f"
echo "To stop: docker compose down"
