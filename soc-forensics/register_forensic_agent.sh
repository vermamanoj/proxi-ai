#!/bin/bash
# Register forensic investigation container as a Proxi workstation

echo "🔧 Registering Forensic Investigation Container with Proxi Core..."

# Configuration
CORE_URL="http://host.docker.internal:4000"  # From inside container
AGENT_NAME="forensic-investigation"
AGENT_URL="http://forensic-investigation:8081"  # Docker network name
AGENT_KEY="${PROXI_AGENT_KEY}"

# Registration payload
PAYLOAD=$(cat <<EOF
{
  "name": "${AGENT_NAME}",
  "url": "${AGENT_URL}",
  "platform": "Linux",
  "description": "SOC Forensic Investigation Training Container - Compromised IdeaForge Production Server",
  "capabilities": ["terminal", "file_read", "log_analysis", "process_inspection", "network_analysis"]
}
EOF
)

# Register with Core
echo "Sending registration to ${CORE_URL}/api/workstations/register..."
curl -X POST "${CORE_URL}/api/workstations/register" \
  -H "Content-Type: application/json" \
  -H "X-Agent-Key: ${AGENT_KEY}" \
  -d "${PAYLOAD}"

echo ""
echo "✅ Registration complete!"
echo ""
echo "🧪 Test the agent:"
echo "   curl http://localhost:5081/health -H 'X-Agent-Key: ${AGENT_KEY}'"
