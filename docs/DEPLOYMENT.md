# Proxi Deployment Guide

## Quick Reference

| Component | Port | Command |
|-----------|------|---------|
| **Core** | 4000 | `.\scripts\deploy-core.ps1` |
| **Frontend** | 4002 | `.\scripts\deploy-frontend.ps1` |
| **Agent** | 8081 | `.\scripts\deploy-agent.ps1 -Register` |
| **All** | - | `.\scripts\deploy-all.ps1` |

---

## Initial Setup (First Time)

### 1. Prerequisites

- Docker Desktop installed and running
- Python 3.10+ (for Windows agent)
- Git

### 2. Clone and Configure

```powershell
git clone https://github.com/vermamanoj/proxi-ai.git
cd proxi-ai

# Create .env from example
Copy-Item .env.example .env

# Edit .env and add your Gemini API key
notepad .env
```

### 3. Deploy Everything

```powershell
# Deploy Core + Frontend + Local Windows Agent
.\scripts\deploy-all.ps1 -IncludeAgent
```

This will:
1. Build and start Core (Docker)
2. Build and start Frontend (Docker)
3. Start local Windows Agent
4. Register the agent with Core

---

## Component-wise Deployment

### Deploy Core Only

```powershell
# Standard deployment
.\scripts\deploy-core.ps1

# Force rebuild (after code changes)
.\scripts\deploy-core.ps1 -Rebuild

# Show logs after starting
.\scripts\deploy-core.ps1 -Logs
```

### Deploy Frontend Only

```powershell
# Standard deployment
.\scripts\deploy-frontend.ps1

# Force rebuild
.\scripts\deploy-frontend.ps1 -Rebuild
```

### Deploy Windows Agent

```powershell
# Start agent and register with Core
.\scripts\deploy-agent.ps1 -Register

# Custom agent name and port
.\scripts\deploy-agent.ps1 -Register -AgentName "my-pc" -Port 8082

# Just start (no registration)
.\scripts\deploy-agent.ps1
```

---

## Agent Registration

Agents must be registered with Core to appear in the UI dropdown.

### Using Script

```powershell
.\scripts\register-agent.ps1 -AgentName "my-agent"

# With all options
.\scripts\register-agent.ps1 `
    -AgentName "finance-pc" `
    -DisplayName "Finance Department PC" `
    -Description "Windows 11 with Excel and SAP" `
    -CoreUrl "http://localhost:4000" `
    -Port 8081 `
    -Capabilities @("terminal", "screenshot", "excel", "sap")
```

### Using API Directly

```powershell
$body = @{
    id = "my-agent"
    name = "My Agent"
    description = "Windows desktop automation"
    workstation_type = "windows"
    host = "host.docker.internal"
    port = 8081
    capabilities = @("terminal", "screenshot", "desktop")
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:4000/api/workstations" -Method POST -ContentType "application/json" -Body $body
```

### Managing Agents

```powershell
# List all agents
Invoke-RestMethod -Uri "http://localhost:4000/api/workstations"

# Check agent health
Invoke-RestMethod -Uri "http://localhost:4000/api/workstations/my-agent/health"

# Delete agent
Invoke-RestMethod -Uri "http://localhost:4000/api/workstations/my-agent" -Method DELETE

# Activate agent (set as default for tool execution)
Invoke-RestMethod -Uri "http://localhost:4000/api/workstations/my-agent/activate" -Method POST
```

---

## Post-Change Deployment

### After Code Changes

```powershell
# Pull latest code
git pull

# Rebuild and restart affected services
.\scripts\deploy-core.ps1 -Rebuild      # If backend changed
.\scripts\deploy-frontend.ps1 -Rebuild  # If frontend changed

# Or rebuild everything
docker compose up -d --build
```

### After Configuration Changes

```powershell
# Just restart (no rebuild needed)
docker compose restart core frontend
```

### Clear All Data and Start Fresh

```powershell
# Stop everything
docker compose down

# Clear persistent data
Remove-Item -Recurse -Force data\*

# Redeploy
.\scripts\deploy-all.ps1 -Rebuild
```

---

## Environment Configurations

### Development (Local)

```env
# .env for local development
GEMINI_API_KEY=your-key-here
RUNTIME_MODE=DEMO
LOG_LEVEL=DEBUG
```

### Production

```env
# .env for production
GEMINI_API_KEY=your-key-here
RUNTIME_MODE=REAL
LOG_LEVEL=INFO
SESSION_TIMEOUT_MINUTES=60
```

---

## Troubleshooting

### Check Service Status

```powershell
# All containers
docker ps

# Service logs
docker compose logs core
docker compose logs frontend

# Follow logs in real-time
docker compose logs -f
```

### Common Issues

| Issue | Solution |
|-------|----------|
| Frontend connection reset | `docker compose restart frontend` |
| Agent not in dropdown | Run `register-agent.ps1` |
| Core not starting | Check `.env` has `GEMINI_API_KEY` |
| Port already in use | `docker compose down` then redeploy |

### Full Reset

```powershell
docker compose down -v
docker system prune -f
.\scripts\deploy-all.ps1 -Rebuild -CleanData
```

---

## URLs Reference

| Service | URL |
|---------|-----|
| Frontend | http://localhost:4002 |
| Core API | http://localhost:4000 |
| API Docs | http://localhost:4000/docs |
| Agent Health | http://localhost:8081/health |

---

*Last updated: 2026-01-27*
