# Forensic Container as Proxi Agent

This guide explains how to set up the forensic investigation container as a full Proxi agent, enabling Gemini to interact with it for SOC training scenarios.

## Why Agent Integration?

Without agent integration, Gemini cannot:
- Execute commands in the forensic container
- Read log files or artifacts
- Inspect running processes
- Analyze network connections
- Perform the actual investigation

**With agent integration**, Gemini becomes a fully autonomous SOC analyst that can investigate the compromised server.

---

## Quick Start

### 1. Stop Existing Forensic Container

```bash
docker stop forensic-investigation
docker rm forensic-investigation
```

### 2. Build New Agent-Enabled Image

```bash
cd soc-forensics
docker build -t proxi-forensics:v2 .
```

### 3. Start with Docker Compose

```bash
# Make sure PROXI_AGENT_KEY is set in your .env file
docker-compose -f docker-compose.forensic.yml up -d
```

This will:
- Start the forensic container on port **5081** (agent API)
- Connect to the main Proxi network
- Run both the fake miner and agent server

### 4. Register with Proxi Core

**Option A: Automatic Registration (Recommended)**
```bash
# From host machine
docker exec forensic-investigation bash /usr/local/bin/register_forensic_agent.sh
```

**Option B: Manual Registration via API**
```bash
curl -X POST http://localhost:4000/api/workstations/register \
  -H "Content-Type: application/json" \
  -H "X-Agent-Key: YOUR_PROXI_AGENT_KEY" \
  -d '{
    "name": "forensic-investigation",
    "url": "http://forensic-investigation:8081",
    "platform": "Linux",
    "description": "SOC Forensic Investigation - Compromised IdeaForge Server"
  }'
```

**Option C: Manual Registration via UI**
1. Open Proxi UI at `http://localhost:4002`
2. Go to **Workstations** tab
3. Click **Add Workstation**
4. Fill in:
   - Name: `forensic-investigation`
   - URL: `http://forensic-investigation:8081`
   - Platform: `Linux`
   - Description: `SOC Forensic Investigation Container`

---

## Verify Agent is Working

### 1. Check Container Status
```bash
docker ps | grep forensic
# Should show: forensic-investigation, Up, 0.0.0.0:5081->8081/tcp
```

### 2. Test Agent Health Endpoint
```bash
curl http://localhost:5081/health \
  -H "X-Agent-Key: YOUR_PROXI_AGENT_KEY"
```

Expected response:
```json
{
  "status": "healthy",
  "platform": "Linux",
  "hostname": "prod-ideaforge-01",
  "metrics": {
    "cpu_percent": 58.2,
    "memory_percent": 45.1,
    "disk_percent": 12.3
  }
}
```

### 3. Test Agent Capabilities
```bash
curl http://localhost:5081/capabilities \
  -H "X-Agent-Key: YOUR_PROXI_AGENT_KEY"
```

Should return available tools:
- `run_terminal_command`
- `read_file`
- `search_logs`
- `list_processes`
- `network_connections`

### 4. Test Command Execution
```bash
curl -X POST http://localhost:5081/execute \
  -H "Content-Type: application/json" \
  -H "X-Agent-Key: YOUR_PROXI_AGENT_KEY" \
  -d '{
    "tool_name": "run_terminal_command",
    "parameters": {"command": "ps aux | head -5"}
  }'
```

---

## Using with Gemini

Once registered, you can prompt Gemini to investigate:

### Example Prompts

**Initial Investigation:**
```
"We have a production server with high CPU usage. 
Switch to the forensic-investigation workstation and start investigating."
```

**Guided Investigation:**
```
"Check the top processes by CPU usage on forensic-investigation.
Then examine the application logs in /var/log/ideaforge-frontend.log."
```

**Autonomous Investigation:**
```
"Investigate the security incident on forensic-investigation.
Find the root cause, identify persistence mechanisms, and document your findings."
```

### What Gemini Can Do

1. **Process Analysis**
   - List running processes
   - Identify suspicious high-CPU processes
   - Check process details and command lines

2. **Log Analysis**
   - Read system logs (`/var/log/messages`, `/var/log/secure`)
   - Read application logs (`/var/log/ideaforge-frontend.log`)
   - Search for specific patterns (RCE, exploits, errors)

3. **Network Analysis**
   - Check active connections with `ss` or `netstat`
   - Identify suspicious outbound connections
   - Verify firewall rules (via OCI config file)

4. **File System Forensics**
   - Read malware files (`/tmp/NCvhHaev`)
   - Check systemd services (`/etc/systemd/system/`)
   - Examine cron jobs and startup scripts

5. **Evidence Collection**
   - Document timeline of events
   - Map persistence mechanisms
   - Identify attack vector

---

## Agent Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Proxi Core (Port 4000)                   │
│  - Gemini LLM orchestration                                 │
│  - Session management                                       │
│  - Agent routing                                            │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      │ HTTP requests with X-Agent-Key
                      │
        ┌─────────────┴─────────────┬─────────────────────┐
        │                           │                     │
        ▼                           ▼                     ▼
┌───────────────┐         ┌─────────────────┐   ┌────────────────┐
│ Linux Agent   │         │ Forensic Agent  │   │ Windows Agent  │
│ (Port 4001)   │         │ (Port 5081)     │   │ (Port 8081)    │
│               │         │                 │   │                │
│ - General     │         │ - Fake miner    │   │ - Desktop      │
│   commands    │         │ - Backdated logs│   │   automation   │
│ - Sandbox     │         │ - Malware files │   │ - OCI console  │
└───────────────┘         │ - Persistence   │   └────────────────┘
                          │ - Investigation │
                          │   tools         │
                          └─────────────────┘
```

---

## Troubleshooting

### Agent Not Responding
```bash
# Check if agent is running
docker logs forensic-investigation --tail 20

# Should see:
# [FORENSIC AGENT] Starting Proxi Forensic Agent on port 8081...
# INFO:     Uvicorn running on http://0.0.0.0:8081
```

### Registration Failed
- Verify `PROXI_AGENT_KEY` matches in both Core and agent
- Check network connectivity: `docker network ls`
- Ensure containers are on same network: `proxi-ai_default`

### 401 Unauthorized
- Agent key mismatch
- Check `.env` file has correct `PROXI_AGENT_KEY`
- Restart containers after changing `.env`

### Fake Miner Not Running
```bash
docker exec forensic-investigation ps aux | grep fake_miner
# Should show: python3 /usr/local/bin/fake_miner.py
```

---

## Network Configuration

### Port Mapping
- **5081** (host) → **8081** (container) - Proxi agent API
- Port 5081 chosen to avoid conflict with main Linux agent on 4001

### Docker Networks
- Container joins `proxi-ai_default` network
- Allows Core to reach agent via hostname: `forensic-investigation:8081`
- Allows agent to reach Core via: `host.docker.internal:4000`

---

## Security Notes

1. **Agent Key Required**: All endpoints require `X-Agent-Key` header
2. **Command Execution**: Agent can run arbitrary commands (by design for investigation)
3. **Network Isolation**: Container should only be accessible from Proxi Core
4. **Demo Environment**: This is a training/demo container, not production

---

## Next Steps

1. ✅ Build and start agent-enabled container
2. ✅ Register with Proxi Core
3. ✅ Verify health and capabilities
4. 🧪 Test with Gemini investigation prompts
5. 🎬 Record demo video for hackathon
6. 📊 Document investigation findings

---

## Files Created

- `forensic_agent.py` - Minimal Proxi agent server
- `docker-compose.forensic.yml` - Compose file with network config
- `register_forensic_agent.sh` - Auto-registration script
- `AGENT_SETUP.md` - This documentation

## Related Documentation

- `../docs/SOC_FORENSIC_SIMULATION.md` - Investigation scenario
- `PROXI_INTEGRATION.md` - Multi-desktop workflow
- `README.md` - Quick start guide
