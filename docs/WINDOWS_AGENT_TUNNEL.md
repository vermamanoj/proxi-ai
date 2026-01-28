# Windows Agent Tunnel Setup (Tailscale)

**Last Updated:** January 28, 2026  
**Purpose:** Connect Windows Agent behind NAT/firewall to Proxi Core

---

## Problem

Your Windows agent on Azure cannot accept inbound traffic from the Internet. Core needs to reach the agent's `/execute` endpoint.

**Solution:** Use Tailscale to create a secure mesh VPN where the Windows agent initiates the connection (outbound only).

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     TAILSCALE MESH NETWORK                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ORACLE CLOUD (Public)                    AZURE (No inbound)               │
│   ─────────────────────                    ──────────────────               │
│   ┌─────────────────┐                      ┌─────────────────┐              │
│   │  Proxi Core     │◄─── Tailscale ──────►│  Windows Agent  │              │
│   │  100.64.0.1     │     WireGuard        │  100.64.0.2     │              │
│   │  Port 4000      │     Encrypted        │  Port 8081      │              │
│   └─────────────────┘                      └─────────────────┘              │
│          │                                                                  │
│          │ Public IP                                                        │
│          ▼                                                                  │
│   ┌─────────────────┐                                                       │
│   │  Frontend       │◄──────────── Users via HTTPS ─────────────────────    │
│   │  proxi.domain   │                                                       │
│   └─────────────────┘                                                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Key Points:**
- Windows agent initiates outbound connection to Tailscale
- No inbound ports needed on Azure
- Core reaches agent via Tailscale IP (100.x.x.x)
- All traffic encrypted with WireGuard

---

## Setup Instructions

### Step 1: Create Tailscale Account

1. Go to https://tailscale.com
2. Sign up with Google/Microsoft/GitHub
3. Note your Tailnet name (e.g., `yourname.ts.net`)

### Step 2: Install on Oracle Linux (Core Server)

```bash
# Install Tailscale
curl -fsSL https://tailscale.com/install.sh | sh

# Authenticate (opens browser or gives URL)
sudo tailscale up

# Get Tailscale IP
tailscale ip -4
# Output: 100.64.0.1 (example)
```

### Step 3: Install on Azure Windows

```powershell
# Install via winget
winget install Tailscale.Tailscale

# Or download from https://tailscale.com/download/windows

# After install, click system tray icon → Connect → Sign in
# Get Tailscale IP:
tailscale ip -4
# Output: 100.64.0.2 (example)
```

### Step 4: Verify Connectivity

From Oracle Linux:
```bash
# Ping Windows agent via Tailscale
ping 100.64.0.2

# Test agent endpoint
curl http://100.64.0.2:8081/health
```

### Step 5: Register Agent with Tailscale IP

Update `backend/registry/workstations.json`:

```json
{
  "win-azure": {
    "id": "win-azure",
    "name": "Windows Agent (Azure)",
    "description": "Azure Windows desktop via Tailscale",
    "workstation_type": "windows",
    "host": "100.64.0.2",
    "port": 8081,
    "capabilities": ["terminal", "screenshot", "desktop", "file_operations"],
    "status": "unknown",
    "is_default": false
  }
}
```

Or via API:
```bash
curl -X POST http://localhost:4000/api/workstations \
  -H "Content-Type: application/json" \
  -d '{
    "id": "win-azure",
    "name": "Windows Agent (Azure)",
    "host": "100.64.0.2",
    "port": 8081,
    "workstation_type": "windows"
  }'
```

---

## Alternative: Oracle Windows VM

If you prefer not to use Tailscale, deploy Windows on Oracle Cloud:

### Benefits
- Same network as Core (private subnet)
- No tunnel needed
- Lower latency

### Setup
1. Create Windows Server 2022 VM on Oracle Cloud
2. Configure security list to allow port 8081 from Core's private IP only
3. Install Python + Proxi agent
4. Register with private IP

---

## Security Considerations

### Tailscale ACLs

Restrict which devices can talk to each other:

```json
// In Tailscale Admin Console → Access Controls
{
  "acls": [
    {
      "action": "accept",
      "src": ["tag:core"],
      "dst": ["tag:agent:8081"]
    }
  ],
  "tagOwners": {
    "tag:core": ["autogroup:admin"],
    "tag:agent": ["autogroup:admin"]
  }
}
```

### Agent API Key

Always set `PROXI_AGENT_KEY` even with Tailscale:

```powershell
# On Windows agent
$env:PROXI_AGENT_KEY = "your-secret-key-here"
uvicorn backend.agent_server:app --host 0.0.0.0 --port 8081
```

---

## Troubleshooting

### Tailscale not connecting

```powershell
# Check status
tailscale status

# Force reconnect
tailscale down
tailscale up
```

### Agent unreachable from Core

```bash
# Check firewall on Windows
netsh advfirewall firewall show rule name=all | findstr 8081

# Add rule if missing
netsh advfirewall firewall add rule name="Proxi Agent" dir=in action=allow protocol=TCP localport=8081
```

### High latency

Tailscale uses DERP relay servers if direct connection fails. Check:
```bash
tailscale netcheck
```

If relay is being used, ensure UDP port 41641 is open for direct WireGuard.

---

## Quick Reference

| Item | Oracle Core | Azure Windows |
|------|-------------|---------------|
| Tailscale IP | 100.64.0.1 | 100.64.0.2 |
| Service Port | 4000 | 8081 |
| Public Access | Yes (frontend, API) | No |
| Agent Key | Set in .env | Set in env var |

---

*For full security details, see [SECURITY_ROADMAP.md](./SECURITY_ROADMAP.md)*
