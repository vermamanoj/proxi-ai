# Windows Agent Setup Guide

**Last Updated:** February 3, 2026  
**Last Commit:** `7536e45` - Add Windows agent service setup script for auto-start on reboot  
**Status:** ✅ Production Ready

## Connecting a Windows Desktop to Proxi Core (Production)

This guide explains how to register a Windows machine as a remote agent that Proxi can control.

---

## Prerequisites

- Windows 10/11 with Python 3.10+
- **Tailscale** installed (for secure connection to production server)
- Admin rights (for some automation features)
- **GEMINI_API_KEY** (optional but recommended for local visual grounding via `/ground` endpoint)

---

## Quick Start (Recommended)

### One-Command Setup

```powershell
# Run the setup script - it handles everything
.\scripts\register-windows-agent.ps1
```

The script will:
1. Check Tailscale connection
2. Set up Python environment
3. Start the agent
4. Show you how to register with production

---

## Manual Setup

### 1. Install Tailscale (Required for Production)

```powershell
# Install Tailscale
winget install Tailscale.Tailscale

# Connect via system tray icon, then get your IP:
tailscale ip -4
# Example output: 100.64.0.5
```

### 2. Clone and Setup

```powershell
git clone https://github.com/vermamanoj/proxi-ai.git
cd proxi-ai

# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install agent-only requirements
pip install -r backend/requirements-agent.txt
```

### 3. Set Environment Variables

```powershell
# Must match PROXI_AGENT_KEY in production .env
$env:PROXI_AGENT_KEY = "your-production-agent-key"

# Optional: Enable local visual grounding (v3.2.0+)
# This allows the agent to use Gemini locally for finding UI elements
$env:GEMINI_API_KEY = "your-gemini-api-key"
```

> **NEW in v3.2.0:** Setting `GEMINI_API_KEY` on the agent enables the `/ground` endpoint for local visual grounding. This significantly improves GUI interaction performance by eliminating round-trips to Core for screenshot analysis.

### 4. Start the Agent

```powershell
python -m uvicorn backend.agent_server:app --host 0.0.0.0 --port 8081
```

### 5. Register with Production Server

**Option A: Edit workstations.json on server** (Recommended)

SSH to your production server and edit `backend/registry/workstations.json`:

```json
{
  "win-desktop": {
    "id": "win-desktop",
    "name": "Windows Desktop",
    "host": "100.64.0.5",
    "port": 8081,
    "workstation_type": "windows",
    "capabilities": ["terminal", "screenshot", "desktop", "file_operations"],
    "is_default": false
  }
}
```

> ⚠️ **IMPORTANT**: The outer JSON key must match the `id` field exactly!
> - ✅ Correct: `"win-desktop": { "id": "win-desktop", ... }`
> - ❌ Wrong: `"my-key": { "id": "different-id", ... }` (causes 404 errors)

Then restart the backend: `docker compose restart core`

**Option B: Via Admin UI**

1. Log in to https://proxi.audista.com as admin
2. Open Settings → Admin Panel
3. Add new workstation with your Tailscale IP

### 6. Verify Connection

From the production server (via Tailscale):
```bash
curl http://100.64.0.5:8081/health
# Should return: {"status": "healthy", ...}
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              Proxi Core (Ubuntu Server / Docker)            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  Auth API   │  │ Session DB  │  │  Gemini Live API    │  │
│  │  (cookies)  │  │  (SQLite)   │  │  (WebRTC/REST)      │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│                          │                                  │
│              Workstation Registry (JSON)                    │
│                  stores agent Tailscale IPs                 │
└──────────────────────────┬──────────────────────────────────┘
                           │
                    Tailscale Mesh VPN
                    (secure, NAT-traversing)
                           │
                           ▼ HTTP requests to agent
┌──────────────────────────────────────────────────────────────┐
│           Windows Agent (Your PC - behind NAT/firewall)      │
│                    Tailscale IP: 100.x.x.x                   │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │ Command Exec │  │ Screenshot   │  │ GUI Automation    │  │
│  │ (PowerShell) │  │ (PIL)        │  │ (pyautogui)       │  │
│  └──────────────┘  └──────────────┘  └───────────────────┘  │
│                                                              │
│  Agent Server (uvicorn :8081)                               │
│  - GET /health    → health check                            │
│  - POST /execute  → run tools (X-Agent-Key auth)            │
└──────────────────────────────────────────────────────────────┘
```

**Key Points:**
- Core initiates connections TO agents (not the reverse)
- Tailscale provides secure mesh networking through NAT/firewalls
- Agent validates requests via `X-Agent-Key` header
- No inbound ports needed on Windows machine

---

## Agent Capabilities

| Capability | Description | Requires |
|------------|-------------|----------|
| **Terminal Commands** | Execute PowerShell/CMD | Base install |
| **Screenshots** | Capture desktop/windows | `pillow` |
| **GUI Automation** | Mouse/keyboard control | `pyautogui` |
| **Window Management** | List/focus windows | `pywinauto` |
| **Clipboard** | Read/write clipboard | `pyperclip` |

---

## Connection Flow

```
1. SETUP (one-time)
   ├── Install Tailscale on both machines
   ├── Both join same Tailscale network (tailnet)
   └── Add agent to workstations.json with Tailscale IP

2. RUNTIME
   ├── User logs in to Proxi (cookie auth)
   ├── User selects Windows agent from dropdown
   ├── Core calls GET http://{tailscale-ip}:8081/health
   │   └── Agent validates X-Agent-Key header
   ├── If healthy, agent is marked "online"
   └── User commands → Core → POST /execute → Agent → Result

3. SECURITY LAYERS
   ├── Cloudflare: Bot protection on frontend
   ├── Session Auth: All API endpoints require login
   ├── Admin Only: Workstation create/delete
   ├── Tailscale: Encrypted mesh, no public exposure
   └── Agent Key: Shared secret validates Core→Agent calls
```

---

## Security Considerations

### Command Guard

The agent uses `CommandGuard` to filter dangerous commands:

```python
# Blocked commands (never executed)
- format, fdisk, diskpart
- Remove-Item -Recurse on system paths
- reg delete on critical keys
- Disabling security features

# Approval required
- Installing software (choco, winget, pip install)
- Modifying registry
- Creating scheduled tasks
- Network configuration changes
```

### Network Security

| Layer | Protection |
|-------|------------|
| **Tailscale** | Encrypted WireGuard tunnel, no public ports |
| **Agent Key** | `PROXI_AGENT_KEY` must match on Core and Agent |
| **Session Auth** | All API calls require valid login cookie |
| **Admin Role** | Only admins can register/delete workstations |

---

## Advanced Configuration

### Complete Demo Server Setup (Recommended)

Use the all-in-one setup script that handles everything:

```powershell
# Full setup: agent + demo apps + auto-start everything
.\scripts\setup-windows-demo.ps1 -All
```

**Script Options:**
| Flag | What it does |
|------|--------------|
| (none) | Install agent dependencies only |
| `-IncludeDemoApps` | Also install Electron demo apps (npm install) |
| `-ScheduleAgent` | Schedule agent auto-start on login (hidden console) |
| `-ScheduleApps` | Schedule Electron apps auto-start on login |
| `-All` | All of the above |
| `-Uninstall` | Remove all scheduled tasks |

**Auto-Installs:**
- Python (via winget if missing)
- Node.js (via winget if missing, when `-IncludeDemoApps`)
- Agent dependencies (pip install)
- Electron app dependencies (npm install)

**Management Commands:**
```powershell
# Stop all
Stop-Process -Name pythonw,electron -Force -ErrorAction SilentlyContinue

# Start all
Start-ScheduledTask -TaskName ProxiAgent
Start-ScheduledTask -TaskName ProxiPricingApp
Start-ScheduledTask -TaskName ProxiCRMApp

# Check agent health
Invoke-WebRequest http://localhost:8081/health

# Uninstall all
.\scripts\setup-windows-demo.ps1 -Uninstall
```

---

### Manual Agent Service Setup (Alternative)

If you only need the agent (no demo apps):

```powershell
.\scripts\setup-agent-service.ps1 -ProjectPath "C:\data\proxi-ai" -Port 8081
```

---

### Demo Electron Apps

| App | Path | Description |
|-----|------|-------------|
| **Pricing System** | `demo-apps/pricing-app` | Enterprise pricing calculator |
| **CRM System** | `demo-apps/crm-app` | Customer relationship management |

**Manual Start:**
```powershell
cd C:\data\proxi-ai\demo-apps\pricing-app && npm start
cd C:\data\proxi-ai\demo-apps\crm-app && npm start
```

### Multiple Agents

Each Windows machine needs a unique `AGENT_NAME`:

```env
# PC 1
AGENT_NAME=dev-workstation

# PC 2  
AGENT_NAME=test-server

# PC 3
AGENT_NAME=build-machine
```

---

## Agent API Reference

These endpoints run on the Windows agent (port 8081):

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Returns agent status, OS info |
| `/execute` | POST | Execute a tool (terminal, screenshot, etc.) |
| `/ground` | POST | **NEW v3.2.0** Visual grounding - find UI element coordinates (requires `GEMINI_API_KEY`) |

### Execute Request

```json
POST /execute
X-Agent-Key: {PROXI_AGENT_KEY}

{
  "tool_name": "run_terminal_command",
  "parameters": {
    "command": "Get-Process | Select-Object -First 5"
  }
}
```

### Health Response

```json
{
  "status": "healthy",
  "os": "Windows",
  "hostname": "WIN-PC",
  "tools_available": ["run_terminal_command", "take_screenshot", ...]
}
```

---

---

## Breaking Changes (v3.2.0 - January 30, 2026)

| Change | Impact | Action Required |
|--------|--------|----------------|
| New `/ground` endpoint | Enables local visual grounding | Set `GEMINI_API_KEY` on agent for best performance |
| New `get_observation` tool | Returns screenshot + UI tree + SoM overlay | No action - backward compatible |
| New `ground_and_click` Core tool | Preferred method for GUI interactions | No action - agents work without it |

*Last updated: 2026-01-30*
