#!/bin/bash
# Proxi Agent Deployment Script (Linux/Docker)
# Usage: ./scripts/deploy-agent-linux.sh [--register] [--core-url URL] [--agent-name NAME]

set -e

# Default values
REGISTER=false
CORE_URL="http://localhost:4000"
AGENT_NAME="linux-agent"
AGENT_DESC="Linux desktop automation agent"
PORT=8081

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --register) REGISTER=true; shift ;;
        --core-url) CORE_URL="$2"; shift 2 ;;
        --agent-name) AGENT_NAME="$2"; shift 2 ;;
        --port) PORT="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

echo "============================================"
echo "  Proxi Agent Deployment (Linux)"
echo "============================================"
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 not found. Install Python 3.10+"
    exit 1
fi
echo "[OK] Python3 found: $(python3 --version)"

# Check/create venv
if [ ! -d "venv" ]; then
    echo "[INFO] Creating virtual environment..."
    python3 -m venv venv
fi

# Activate venv
echo "[INFO] Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "[INFO] Installing agent dependencies..."
pip install -q -r backend/requirements-agent.txt

# Start agent
echo "[INFO] Starting Proxi Agent on port $PORT..."
python -m uvicorn backend.agent_server:app --host 0.0.0.0 --port $PORT &
AGENT_PID=$!

# Wait for agent to be ready
sleep 3

# Check agent health
if curl -s "http://localhost:$PORT/health" > /dev/null; then
    echo "[SUCCESS] Agent is running at http://localhost:$PORT"
else
    echo "[WARNING] Agent may not be ready yet"
fi

# Register with Core if requested
if [ "$REGISTER" = true ]; then
    echo ""
    echo "[INFO] Registering agent with Core at $CORE_URL..."
    
    curl -s -X POST "$CORE_URL/api/workstations" \
        -H "Content-Type: application/json" \
        -d "{
            \"id\": \"$AGENT_NAME\",
            \"name\": \"Linux Agent ($AGENT_NAME)\",
            \"description\": \"$AGENT_DESC\",
            \"workstation_type\": \"linux\",
            \"host\": \"host.docker.internal\",
            \"port\": $PORT,
            \"capabilities\": [\"terminal\", \"file_operations\", \"git\", \"python\"]
        }" && echo "[SUCCESS] Agent registered!" || echo "[ERROR] Registration failed"
fi

echo ""
echo "Agent URL: http://localhost:$PORT"
echo "Health:    http://localhost:$PORT/health"
echo ""
echo "Press Ctrl+C to stop the agent"

# Wait for agent process
wait $AGENT_PID
