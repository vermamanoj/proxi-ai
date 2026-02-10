# Proxi Deployment Guide

**Last Updated:** January 30, 2026  
**Last Commit:** `0376b4d` - Add SoM overlay, combined observation, and local Gemini grounding  
**Status:** ⚠️ Testing Pending

> **Note:** This document has been restructured. See the new documentation:
> - [docs/DEPLOY_OPS.md](./docs/DEPLOY_OPS.md) - Deployment & Operations
> - [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) - System Architecture
> - [docs/SECURITY_ROADMAP.md](./docs/SECURITY_ROADMAP.md) - Security Roadmap
> - [docs/FEATURES.md](./docs/FEATURES.md) - Feature Tracker
>
> The original content is archived in `docs/archive/DEPLOYMENT.md`.

---

## ⚠️ Breaking Changes (v3.2.0 - January 30, 2026)

| Change | Component | Action Required |
|--------|-----------|-----------------|
| New `/ground` endpoint | Windows Agent | **Optional:** Set `GEMINI_API_KEY` on agent for local visual grounding |
| New `get_observation` tool | All Agents | No action - backward compatible |
| New `ground_and_click` tool | Core | No action - new capability for GUI automation |
| Updated `look_at_screen` | Core | No action - now returns Set-of-Mark overlay with numbered elements |

**For best GUI automation performance**, set `GEMINI_API_KEY` on Windows agents:
```powershell
$env:GEMINI_API_KEY = "your-api-key"
```

---

## Quick Start

```bash
# Clone and configure
git clone https://github.com/vermamanoj/proxi-ai.git
cd proxi-ai
cp .env.example .env
# Edit .env with your GEMINI_API_KEY and PROXI_AGENT_KEY
# NEW: Also set GEMINI_API_KEY on Windows agents for local visual grounding

# Run the full deployment script
./deploy.sh

# Check service status
./deploy.sh --status
```

### Common Operations

| Task | Command |
|------|---------|
| Full deploy (pull + docker + nginx) | `./deploy.sh` |
| Rebuild Docker only | `./deploy.sh --docker` |
| Update nginx config | `./deploy.sh --nginx` |
| View logs | `./deploy.sh --logs` |
| Check status | `./deploy.sh --status` |
| Restart containers | `./deploy.sh --restart` |

For detailed deployment instructions, see [docs/DEPLOY_OPS.md](./docs/DEPLOY_OPS.md).

---

## 1. ARCHITECTURE OVERVIEW (Legacy - See docs/ARCHITECTURE.md)

### 1.1 Core/Agent Split Architecture

Proxi uses a security-focused split architecture where sensitive data (API keys, user DB) stays in Core while tool execution happens in isolated Agents.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PROXI SPLIT ARCHITECTURE                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────────┐         HTTPS              ┌─────────────────────────┐  │
│   │  User's      │───────────────────────────▶│  FRONTEND (Port 4002)   │  │
│   │  Mobile      │                            │  React + Vite           │  │
│   │  Browser     │                            │  Agent Selector UI      │  │
│   └──────────────┘                            └───────────┬─────────────┘  │
│                                                           │                │
│                                                           ▼                │
│                                               ┌─────────────────────────┐  │
│                                               │  PROXI CORE (Port 4000) │  │
│                                               │  ✓ GEMINI_API_KEY       │  │
│                                               │  ✓ User Database        │  │
│                                               │  ✓ Session Management   │  │
│                                               │  ✓ LLM Orchestration    │  │
│                                               │  ✓ Agent Proxy Router   │  │
│                                               └───────────┬─────────────┘  │
│                                                           │                │
│                              HTTP /execute                │                │
│                    ┌──────────────────────────────────────┤                │
│                    ▼                                      ▼                │
│        ┌─────────────────────────┐          ┌─────────────────────────┐    │
│        │  PROXI AGENT (4001)     │          │  WINDOWS AGENT (Remote) │    │
│        │  Linux Container        │          │  Windows Server         │    │
│        │  ✗ No API Keys          │          │  ✗ No API Keys          │    │
│        │  ✗ No User Data         │          │  ✗ No User Data         │    │
│        │  ✓ Tool Execution Only  │          │  ✓ Desktop Automation   │    │
│        └─────────────────────────┘          └─────────────────────────┘    │
│              BLAST RADIUS                         BLAST RADIUS             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Security Benefit:** If LLM tool execution is compromised, only the Agent container is affected. Core (with API keys, user data) remains isolated.

### 1.2 Component Responsibilities

| Component | Port | Purpose | Has API Keys? |
|-----------|------|---------|---------------|
| **Frontend** | 4002 | React UI, Agent Selector | No |
| **Proxi Core** | 4000 | LLM orchestration, Auth, Sessions | **Yes** |
| **Proxi Agent** | 4001 | Isolated tool execution (Linux) | No |
| **Windows Agent** | 8081 | Remote desktop automation | No |

### 1.3 Docker Services

```bash
# Quick Start
docker compose up -d

# Services started:
# - proxi-ai-core-1      Port 4000  (needs GEMINI_API_KEY in .env)
# - proxi-ai-agent-1     Port 4001  (no keys needed)
# - proxi-ai-frontend-1  Port 4002
```

| Service | Image | Dockerfile | Description |
|---------|-------|------------|-------------|
| `core` | proxi-core | `backend/Dockerfile` | Full backend with DB, Auth, LLM |
| `agent` | proxi-agent | `backend/Dockerfile.agent` | Minimal, tools only |
| `frontend` | proxi-frontend | `frontend/Dockerfile` | React static build |

### 1.4 Remote Agent Networking (Tailscale)

For agents behind NAT/firewall without inbound access, use **Tailscale** to create a secure mesh VPN.

#### Why Tailscale?
| Feature | Tailscale | ngrok | Cloudflare Tunnel |
|---------|-----------|-------|-------------------|
| Stable URL/IP | ✅ Fixed 100.x.x.x | ❌ Random (free) | ✅ Fixed |
| Cost | Free | $8/mo for fixed | Free |
| Antivirus issues | ✅ None | ✅ None | ⚠️ Flagged as malware |
| Multi-agent mesh | ✅ Yes | ❌ No | ❌ No |

#### Setup Steps

**1. Create Tailscale Account**
```bash
# Visit https://login.tailscale.com (Google/Microsoft SSO)
# Go to Settings → Keys → Generate auth key (reusable, no expiry)
# Save: tskey-auth-xxxxxxxxxxxxx
```

**2. Install on Linux Agent**
```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up --authkey=tskey-auth-xxxxxxxxxxxxx
# Note the IP: tailscale ip -4  (e.g., 100.64.0.2)
```

**3. Install on Windows Agent**
```powershell
# Option A: GUI
winget install Tailscale.Tailscale
# Login via system tray → Google SSO

# Option B: Headless (for servers)
msiexec /i tailscale-setup.msi /quiet TS_AUTHKEY=tskey-auth-xxxxxxxxxxxxx
tailscale status  # Verify connection
```

**4. Install on Docker (Sidecar)**
```yaml
# docker compose.yml
services:
  tailscale:
    image: tailscale/tailscale:latest
    hostname: proxi-agent
    environment:
      - TS_AUTHKEY=tskey-auth-xxxxxxxxxxxxx
      - TS_STATE_DIR=/var/lib/tailscale
    volumes:
      - tailscale-state:/var/lib/tailscale
    cap_add:
      - NET_ADMIN
    network_mode: host

  agent:
    depends_on: [tailscale]
    network_mode: "service:tailscale"
```

**5. Register Agent with Core**
```bash
# Get Tailscale IP
tailscale ip -4  # e.g., 100.64.0.2

# Register with Core
curl -X POST http://core-server:4000/api/workstations \
  -H "Content-Type: application/json" \
  -d '{
    "id": "win-agent-1",
    "name": "Windows Desktop",
    "host": "100.64.0.2",
    "port": 4001,
    "workstation_type": "windows"
  }'
```

#### Environment Variables
Add to `.env` for automated deployments:
```bash
TAILSCALE_AUTHKEY=tskey-auth-xxxxxxxxxxxxx
```

---

## 2. NEW FEATURES ROADMAP

### 2.1 Landing Page (Public)
**Priority:** HIGH  
**Status:** Pending

#### Design
Public marketing page at root `/` - no auth required:
```
┌─────────────────────────────────────────────────────────────────┐
│  PROXI - Your AI Desktop Agent                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [Hero Section]                                                 │
│  "Control your desktop from anywhere"                           │
│  - Demo video / animated screenshot                             │
│  - Key features list                                            │
│                                                                 │
│  [How It Works]                                                 │
│  - Visual flow diagram                                          │
│                                                                 │
│  [Call to Action]                                               │
│  [Login] [Learn More]                                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Authentication System
**Priority:** HIGH  
**Status:** Pending

#### Design
```
┌─────────────────────────────────────────────────────────────────┐
│  LOGIN FLOW                                                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. User visits proxi.audista.com (public landing page)         │
│  2. User clicks "Login" → /login page                           │
│  3. User enters credentials                                     │
│  4. POST /api/auth/login → validate → set HTTP-only cookie      │
│  5. Redirect to /dashboard (workstation selection)              │
│  6. All /app/* and /api/* routes require valid session          │
│  7. Landing page (/) always public                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### Implementation Files
- `frontend/src/pages/Login.tsx` - Login form UI
- `frontend/src/hooks/useAuth.ts` - Auth state management
- `frontend/src/components/ProtectedRoute.tsx` - Route guard
- `backend/auth/auth_service.py` - Session validation
- `backend/auth/users.json` - Local user store (demo)

#### Security Considerations
- HTTP-only cookies (XSS protection)
- CSRF tokens for form submissions
- Session timeout (30 minutes idle)
- Rate limiting on login attempts
- Credentials in DevPost submission only

### 2.3 Registered Workstations
**Priority:** HIGH  
**Status:** Pending

#### Concept
Users can register multiple backend machines. Each workstation has:
- Unique ID and friendly name
- Connection status (online/offline)
- Installed capabilities (tools available)
- Last activity timestamp

#### UI Design
```
┌─────────────────────────────────────────────────────────────┐
│  PROXI CONSOLE - My Workstations                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ● linux-container   Ubuntu Container         🟢 Online    │
│    └─ Terminal, Docker, Git, Python                        │
│    └─ Last active: Just now                                │
│    [Connect]                                                │
│                                                             │
│  ● sales-win-vm      Windows Server 2022      🟢 Online    │
│    └─ CRM, Pricing Tool, PowerPoint, Outlook               │
│    └─ Last active: 2 minutes ago                           │
│    [Connect]                                                │
│                                                             │
│  ○ finance-desktop   Windows 11              ⚫ Offline    │
│    └─ Excel, SAP, QuickBooks                               │
│    └─ Last active: 1 week ago                              │
│    [Start VM]                                               │
│                                                             │
│  [+ Register New Workstation]                               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### Implementation Files
- `frontend/src/pages/Dashboard.tsx` - Workstation list
- `frontend/src/components/WorkstationCard.tsx` - Individual card
- `backend/registry/workstation_registry.py` - Registry service
- `backend/registry/workstations.json` - Workstation config

#### API Endpoints
```
GET  /api/workstations                 - List all registered
POST /api/workstations                 - Register new
GET  /api/workstations/{id}/status     - Health check
POST /api/workstations/{id}/connect    - Establish connection
POST /api/workstations/{id}/start      - Start VM (if cloud)
```

### 2.4 Enhanced Approval Mechanism
**Priority:** HIGH  
**Status:** Pending

#### Current Problem
- Approval is inline "Yes/No" - easy to miss
- No clear indication of risk level
- No timeout behavior

#### Proposed Design
```
┌─────────────────────────────────────────────────────────────────┐
│  ⚠️  ACTION REQUIRES APPROVAL                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  The agent wants to execute:                                    │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  pip install pandas numpy                               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Risk Level: 🟡 MODERATE                                        │
│  Reason: Package installation can modify system                 │
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐                          │
│  │   APPROVE    │    │    DENY      │                          │
│  └──────────────┘    └──────────────┘                          │
│                                                                 │
│  Auto-decline in: 30 seconds                                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### Risk Levels
| Level | Color | Description | Examples |
|-------|-------|-------------|----------|
| SAFE | 🟢 | Read-only operations | ls, cat, Get-Process |
| MODERATE | 🟡 | Reversible changes | pip install, create file |
| HIGH | 🔴 | Potentially destructive | delete file, stop service |
| BLOCKED | ⛔ | Never allowed | format, rm -rf / |

### 2.5 Escalate to Human (UI)
**Priority:** HIGH  
**Status:** Pending

#### Current Problem
- Agent logs "escalate_to_human" but user doesn't see it
- No way for user to intervene/respond

#### Proposed Design
```
┌─────────────────────────────────────────────────────────────────┐
│  🚨 AGENT NEEDS YOUR HELP                                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  The agent encountered a situation requiring human judgment:    │
│                                                                 │
│  "I found multiple files matching 'brand_template.pptx'.        │
│   Please clarify which one to use:                              │
│   1. C:\Users\Demo\Downloads\brand_template.pptx                │
│   2. C:\Users\Demo\Desktop\brand_template_v2.pptx"              │
│                                                                 │
│  [Reply to agent...]                                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.6 Mock Applications Server
**Priority:** MEDIUM  
**Status:** Pending

#### Current State
- Static HTML files in `demo/` folder
- Opened via `file://` protocol

#### Proposed Enhancement
Run a simple Flask server on Windows backend that serves mock apps:

```python
# mock_apps_server.py
from flask import Flask, render_template
app = Flask(__name__)

@app.route('/crm')
def crm():
    return render_template('crm.html')

@app.route('/pricing')
def pricing():
    return render_template('pricing-tool.html')

@app.route('/proposal')
def proposal():
    return render_template('proposal-template.html')

if __name__ == '__main__':
    app.run(port=8081)
```

Benefits:
- More realistic URLs (`http://localhost:8081/crm`)
- Can add dynamic data (timestamps, session info)
- No `file://` protocol in screenshots

---

## 3. SECURITY

### 3.1 OS Command Guardrails
**CRITICAL:** Prevent dangerous system commands

#### Blocked Commands (NEVER executed)
```python
BLOCKED_COMMANDS = [
    # Destructive file operations
    r'rm\s+-rf\s+/',           # rm -rf /
    r'del\s+/[sS]\s+/[qQ]',    # del /s /q (Windows recursive delete)
    r'format\s+[a-zA-Z]:',     # format C:
    r'mkfs\.',                  # mkfs.ext4
    r'dd\s+if=',               # dd if=
    
    # System shutdown/reboot
    r'shutdown',               # shutdown
    r'reboot',                 # reboot
    r'halt',                   # halt
    r'init\s+[06]',            # init 0 or 6
    
    # Security bypass
    r':(){ :\|:& };:',         # fork bomb
    r'>\s*/dev/sd',            # write to disk
    r'reg\s+delete\s+HKLM',    # registry delete (machine)
    r'bcdedit',                # boot config
    
    # Privilege escalation
    r'net\s+user\s+.*\s+/add', # add user
    r'net\s+localgroup\s+administrators', # add to admins
    r'passwd\s+root',          # change root password
    r'chmod\s+777\s+/',        # chmod 777 root
    r'chown\s+root',           # change to root ownership
]
```

#### Approval Required Commands
```python
APPROVAL_REQUIRED = [
    # Package installation
    r'pip\s+install',          # package install
    r'npm\s+install',          # package install
    r'choco\s+install',        # chocolatey install
    r'apt\s+install',          # apt install
    
    # Process/Service control
    r'Stop-Process',           # kill process
    r'taskkill',               # kill task
    r'net\s+stop',             # stop service
    r'systemctl\s+stop',       # stop systemd service
    
    # File deletion (non-recursive)
    r'Remove-Item',            # delete file
    r'rm\s+(?!-rf)',           # delete file (not recursive)
    r'del\s+',                 # delete file (Windows)
    r'unlink',                 # unlink file
    
    # File overwrite
    r'>\s+[^/]',               # redirect overwrite
    r'Set-Content',            # PowerShell overwrite
    r'Out-File',               # PowerShell write file
    
    # Privilege-related (non-blocked)
    r'sudo\s+',                # sudo commands
    r'runas\s+',               # Windows runas
]
```

### 3.2 File Operation Guardrails
**CRITICAL:** Prevent accidental data loss

```python
# Protected paths - NEVER delete or overwrite
PROTECTED_PATHS = [
    r'C:\\Windows',
    r'C:\\Program Files',
    r'/etc/',
    r'/usr/',
    r'/bin/',
    r'/boot/',
    r'.git/',
    r'.env',
    r'*.pem',
    r'*.key',
]

# Require approval for these extensions
SENSITIVE_EXTENSIONS = [
    '.exe', '.dll', '.sys',    # Windows executables
    '.sh', '.bash',            # Shell scripts
    '.ps1', '.bat', '.cmd',    # Windows scripts
    '.pem', '.key', '.crt',    # Certificates
    '.db', '.sqlite',          # Databases
]
```

#### Implementation
```python
# tools/command_guard.py
import re
from typing import Tuple

class CommandGuard:
    def check_command(self, command: str) -> Tuple[bool, str, bool]:
        """
        Returns: (allowed, reason, needs_approval)
        """
        # Check blocked
        for pattern in BLOCKED_COMMANDS:
            if re.search(pattern, command, re.IGNORECASE):
                return (False, f"Command blocked: matches '{pattern}'", False)
        
        # Check approval required
        for pattern in APPROVAL_REQUIRED:
            if re.search(pattern, command, re.IGNORECASE):
                return (True, f"Requires approval: matches '{pattern}'", True)
        
        return (True, "Command allowed", False)
```

### 3.2 Network Security

#### Frontend Server (Oracle Ubuntu)
```bash
# UFW Firewall Rules
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP (redirect to HTTPS)
sudo ufw allow 443/tcp     # HTTPS
sudo ufw enable
```

#### Backend Server (Windows)
- No public IP (private subnet or Tailscale only)
- Windows Firewall: Allow only Tailscale network
- RDP disabled or restricted to specific IPs

### 3.3 API Security
```python
# Rate limiting
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)

@app.post("/api/auth/login")
@limiter.limit("5/minute")  # 5 attempts per minute
async def login(request: Request):
    pass

@app.post("/api/vision")
@limiter.limit("30/minute")  # 30 requests per minute
async def vision(request: Request):
    pass
```

---

## 4. DEPLOYMENT SCRIPTS

### 4.1 Frontend Deployment (Oracle Ubuntu)

#### `scripts/deploy-frontend.sh`
```bash
#!/bin/bash
set -e

echo "=== PROXI Frontend Deployment ==="

# Variables
REPO_URL="https://github.com/yourusername/proxi-ai.git"
DEPLOY_DIR="/var/www/proxi"
NGINX_CONF="/etc/nginx/sites-available/proxi"

# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y nginx nodejs npm certbot python3-certbot-nginx

# Clone/update repository
if [ -d "$DEPLOY_DIR" ]; then
    cd $DEPLOY_DIR && git pull
else
    sudo git clone $REPO_URL $DEPLOY_DIR
fi

# Build frontend
cd $DEPLOY_DIR/frontend
npm install
npm run build

# Copy build to nginx
sudo rm -rf /var/www/html/proxi
sudo cp -r dist /var/www/html/proxi

# Configure nginx
sudo tee $NGINX_CONF > /dev/null <<EOF
server {
    listen 80;
    server_name proxi.audista.com;
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl;
    server_name proxi.audista.com;

    ssl_certificate /etc/letsencrypt/live/proxi.audista.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/proxi.audista.com/privkey.pem;

    root /var/www/html/proxi;
    index index.html;

    # Frontend routes
    location / {
        try_files \$uri \$uri/ /index.html;
    }

    # API proxy to backend (via Tailscale)
    location /api {
        proxy_pass http://100.x.x.x:8080;  # Tailscale IP
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_read_timeout 300s;
    }
}
EOF

# Enable site
sudo ln -sf $NGINX_CONF /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# SSL certificate
sudo certbot --nginx -d proxi.audista.com --non-interactive --agree-tos -m your@email.com

echo "=== Frontend deployment complete ==="
```

### 4.2 Backend Deployment (Windows)

#### `scripts/deploy-backend.ps1`
```powershell
# Proxi Backend Deployment Script for Windows
# Run as Administrator

Write-Host "=== PROXI Backend Deployment ===" -ForegroundColor Green

# Variables
$PROXI_DIR = "C:\Proxi"
$PYTHON_VERSION = "3.12"
$TAILSCALE_URL = "https://pkgs.tailscale.com/stable/tailscale-setup-latest.exe"

# Create directory
if (-not (Test-Path $PROXI_DIR)) {
    New-Item -ItemType Directory -Path $PROXI_DIR
}

# Install Chocolatey if not present
if (-not (Get-Command choco -ErrorAction SilentlyContinue)) {
    Set-ExecutionPolicy Bypass -Scope Process -Force
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
    iex ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))
}

# Install Python
choco install python --version=$PYTHON_VERSION -y
refreshenv

# Install Git
choco install git -y
refreshenv

# Install Tailscale
Write-Host "Installing Tailscale..." -ForegroundColor Yellow
Invoke-WebRequest -Uri $TAILSCALE_URL -OutFile "$env:TEMP\tailscale-setup.exe"
Start-Process -FilePath "$env:TEMP\tailscale-setup.exe" -ArgumentList "/quiet" -Wait

# Clone repository
cd $PROXI_DIR
if (Test-Path ".git") {
    git pull
} else {
    git clone https://github.com/yourusername/proxi-ai.git .
}

# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Create environment file
@"
GEMINI_API_KEY=your_api_key_here
PROXI_HOST=0.0.0.0
PROXI_PORT=8080
"@ | Out-File -FilePath ".env" -Encoding utf8

# Install Virtual Display Driver (for headless operation)
Write-Host "Download Virtual Display Driver from:" -ForegroundColor Yellow
Write-Host "https://github.com/VirtualDrivers/Virtual-Display-Driver/releases" -ForegroundColor Cyan

# Create startup script
@"
@echo off
cd /d $PROXI_DIR
call venv\Scripts\activate.bat
python -m uvicorn main:app --host 0.0.0.0 --port 8080
"@ | Out-File -FilePath "$PROXI_DIR\start-proxi.bat" -Encoding ascii

# Create Windows service (optional)
Write-Host "To run as Windows Service, use NSSM:" -ForegroundColor Yellow
Write-Host "choco install nssm -y" -ForegroundColor Cyan
Write-Host "nssm install ProxiBackend $PROXI_DIR\start-proxi.bat" -ForegroundColor Cyan

Write-Host "=== Backend deployment complete ===" -ForegroundColor Green
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Run 'tailscale up' to connect to Tailscale network" -ForegroundColor White
Write-Host "2. Update .env with your GEMINI_API_KEY" -ForegroundColor White
Write-Host "3. Run start-proxi.bat to start the server" -ForegroundColor White
```

### 4.3 Tailscale Setup

#### On Frontend Server (Ubuntu)
```bash
# Install Tailscale
curl -fsSL https://tailscale.com/install.sh | sh

# Authenticate
sudo tailscale up

# Get IP
tailscale ip -4
# Example: 100.100.100.1
```

#### On Backend Server (Windows)
```powershell
# After installing via deploy script
tailscale up

# Get IP
tailscale ip -4
# Example: 100.100.100.2
```

#### Update Nginx Config
Replace `100.x.x.x` with actual Tailscale IP of Windows backend.

### 4.4 Linux Container Deployment (Oracle Ubuntu)

Run a Proxi agent container on the same Ubuntu server for always-on Linux automation:

#### Dockerfile for Linux Agent
```dockerfile
# backend/Dockerfile.linux-agent
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git curl wget \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8081

# Run
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8081"]
```

#### Docker Compose Setup
```yaml
# docker compose.yml
version: '3.8'
services:
  linux-agent:
    build:
      context: ./backend
      dockerfile: Dockerfile.linux-agent
    container_name: proxi-linux-agent
    restart: unless-stopped
    ports:
      - "127.0.0.1:8081:8081"
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - WORKSTATION_TYPE=linux
    volumes:
      - ./workspace:/workspace  # Shared workspace for file operations
    networks:
      - proxi-network

networks:
  proxi-network:
    driver: bridge
```

#### Nginx Routing for Linux Agent
```nginx
# Add to proxi nginx config
location /api/linux {
    proxy_pass http://127.0.0.1:8081;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

#### Benefits
- **Always available** - runs on always-free Oracle tier
- **Shows multi-platform** - judges see both Linux and Windows
- **Terminal automation** - git, docker, python, etc.
- **No VDD needed** - headless by design

---

## 5. SCRIPTS REFERENCE (CONSOLIDATED)

### 5.1 Quick Reference Table

| Script | Location | Purpose | When to Use |
|--------|----------|---------|-------------|
| `setup.sh` | Root | Initial Ubuntu server setup | First time Oracle setup |
| `setup_windows.ps1` | Root | Windows dev environment | First time Windows dev setup |
| `deploy.sh` | Root | Docker Compose deployment | Local/dev deployment |
| `deploy-frontend.sh` | `scripts/` | Oracle Ubuntu frontend | Production frontend deploy |
| `deploy-backend.ps1` | `scripts/` | Windows Server backend | Production Windows deploy |
| `deploy-linux-agent.sh` | `scripts/` | Linux container agent | Deploy always-on Linux agent |
| `docker compose.yml` | Root | Full stack (dev mode) | Local development |

### 5.2 Deployment Order

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     DEPLOYMENT ORDER                                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  STEP 1: Oracle Ubuntu Server (Frontend + Linux Agent)                  │
│  ─────────────────────────────────────────────────────                  │
│  a) SSH into Oracle Ubuntu instance                                     │
│  b) Run: sudo bash setup.sh                    # Install Docker, Nginx  │
│  c) Log out and log back in (for Docker permissions)                    │
│  d) Run: bash scripts/deploy-frontend.sh       # Deploy frontend        │
│  e) Run: bash scripts/deploy-linux-agent.sh    # Deploy Linux agent     │
│  f) Verify: curl http://localhost:8081/health  # Check Linux agent      │
│                                                                         │
│  STEP 2: Windows Server (Desktop Backend) - Optional for demo           │
│  ─────────────────────────────────────────────                          │
│  a) RDP into Windows Server VM                                          │
│  b) Run PowerShell as Admin                                             │
│  c) Run: .\scripts\deploy-backend.ps1          # Install all deps       │
│  d) Edit .env with GEMINI_API_KEY                                       │
│  e) Run: tailscale up                          # Connect to network     │
│  f) Run: .\run_proxi.bat                       # Start backend          │
│                                                                         │
│  STEP 3: Connect Networks                                               │
│  ────────────────────────                                               │
│  a) Get Windows Tailscale IP: tailscale ip -4                           │
│  b) Update Oracle Nginx config with Windows IP                          │
│  c) Test: curl https://proxi.audista.com/api/health                     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 5.3 Script Details

#### Root Scripts (Development/Setup)

**`setup.sh`** - Ubuntu Initial Setup
```bash
# Purpose: Install Docker, Nginx on fresh Ubuntu server
# Prerequisites: Fresh Ubuntu 22.04+, sudo access
# Run as: sudo bash setup.sh
# Output: Docker, Nginx installed and running
```

**`setup_windows.ps1`** - Windows Dev Environment
```powershell
# Purpose: Create venv, install Python deps, test GUI access
# Prerequisites: Python 3.10+, Administrator
# Run as: Right-click → Run as Administrator
# Output: venv created, .env template, run_proxi.bat
```

**`deploy.sh`** - Docker Compose Deployment
```bash
# Purpose: Build and run Core + Agent + Frontend via docker compose
# Prerequisites: Docker, .env file with GEMINI_API_KEY
# Run as: ./deploy.sh
# Output: Containers running on ports 4000 (Core), 4001 (Agent), 4002 (Frontend)
```

#### Production Scripts (`scripts/`)

**`scripts/deploy-frontend.sh`** - Oracle Frontend Deployment
```bash
# Purpose: Deploy React frontend to Oracle Ubuntu with Nginx + SSL
# Prerequisites: Oracle Ubuntu server, domain configured
# Run as: bash scripts/deploy-frontend.sh
# Output: Frontend at https://proxi.audista.com
```

**`scripts/deploy-backend.ps1`** - Windows Backend Deployment  
```powershell
# Purpose: Full Windows Server setup with Python, Tailscale, VDD
# Prerequisites: Windows Server 2022, Administrator, RDP access
# Run as: PowerShell as Administrator
# Output: Backend ready on port 8080, Tailscale connected
```

**`scripts/deploy-linux-agent.sh`** - Linux Container Agent
```bash
# Purpose: Deploy Alpine-based Linux agent container
# Prerequisites: Docker on Oracle Ubuntu
# Run as: bash scripts/deploy-linux-agent.sh
# Output: Linux agent at http://localhost:8081
```

### 5.4 Workstation Registry Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                 WORKSTATION REGISTRY ARCHITECTURE                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────┐     ┌─────────────────────────────────┐       │
│  │  FRONTEND           │     │  BACKEND (when available)       │       │
│  │  Static Fallback    │────▶│  Dynamic Registry               │       │
│  │                     │     │                                 │       │
│  │  config/            │     │  registry/                      │       │
│  │   workstations.ts   │     │   workstation_registry.py       │       │
│  │                     │     │                                 │       │
│  │  • Default config   │     │  • Health checks                │       │
│  │  • Works offline    │     │  • Real-time status             │       │
│  │  • 2 workstations   │     │  • Capability discovery         │       │
│  └─────────────────────┘     └─────────────────────────────────┘       │
│                                                                         │
│  FLOW:                                                                  │
│  1. Frontend loads → tries GET /api/workstations                        │
│  2. If backend responds → use dynamic data                              │
│  3. If backend down → use static config/workstations.ts                 │
│  4. Frontend polls health every 30 seconds                              │
│                                                                         │
│  DATA STORAGE:                                                          │
│  • Dev/Demo: In-memory (Python dict)                                    │
│  • Production: SQLite or JSON file                                      │
│  • Enterprise: PostgreSQL/Redis                                         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 6. HEADLESS OPERATION (NO RDP)

### 6.1 The Problem
When RDP is disconnected:
- Screenshots fail (no display buffer)
- UI automation fails
- Mouse/keyboard not delivered

### 6.2 Solution: Virtual Display Driver

#### Installation
1. Download from: https://github.com/VirtualDrivers/Virtual-Display-Driver/releases
2. Extract and run VDC (Virtual Display Control)
3. Click "Install"
4. Verify in Device Manager → Display Adapters

#### Configuration
```xml
<!-- C:\VirtualDisplayDriver\vdd_settings.xml -->
<VirtualDisplayDriver>
  <Monitors>
    <Monitor>
      <Width>1920</Width>
      <Height>1080</Height>
      <RefreshRate>60</RefreshRate>
    </Monitor>
  </Monitors>
</VirtualDisplayDriver>
```

### 6.3 Alternative: Console Session Trick

Create a scheduled task that switches to console on RDP disconnect:

```batch
:: keep-session-alive.bat
(qwinsta | findstr /r "Active" >NUL) || tscon 1 /dest:console
```

Task Scheduler settings:
- Trigger: On disconnect from user session
- Action: Run the batch file
- Run whether user is logged on or not

---

## 7. TESTING

### 7.1 Local Testing Checklist
```
□ Frontend builds without errors (npm run build)
□ Backend starts without errors (python main.py)
□ Login page renders
□ Authentication works
□ Workstation list loads
□ Chat interface opens
□ Voice input works
□ Text input works
□ Screenshot capture works
□ Click automation works
□ PPT tools work
□ Mock apps accessible
```

### 7.2 Integration Testing
```bash
# Test API endpoints
curl -X POST https://proxi.audista.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","password":"<YOUR_PASSWORD>"}'

# Test vision endpoint (with auth cookie)
curl -X POST https://proxi.audista.com/api/vision \
  -H "Content-Type: application/json" \
  -H "Cookie: session=..." \
  -d '{"message":"What time is it?"}'

# Test workstation status
curl https://proxi.audista.com/api/workstations/1/status \
  -H "Cookie: session=..."
```

### 7.3 End-to-End Demo Test
1. Open mobile browser to proxi.audista.com
2. Login with demo credentials
3. Select "sales-win-vm" workstation
4. Issue voice command: "Open the CRM application"
5. Verify screenshot shows CRM
6. Issue command: "What is the customer lifetime value?"
7. Verify agent navigates tabs and reports data
8. Issue command: "Find PowerPoint templates in Downloads"
9. Verify file search results
10. Issue command: "Send me a screenshot"
11. Verify screenshot appears in chat

---

## 8. MONITORING & LOGGING

### 8.1 Log Files
```
Backend:
  proxi_debug.log      - Detailed execution log
  proxi_error.log      - Errors only

Frontend:
  Browser console      - Runtime errors
  Network tab          - API call traces
```

### 8.2 Health Check Endpoint
```python
@app.get("/api/health")
async def health():
    return {
        "status": "healthy",
        "version": "3.0.0",
        "uptime": get_uptime(),
        "gemini_connected": check_gemini(),
        "desktop_available": check_desktop()
    }
```

### 8.3 Metrics to Track
- API response times
- Screenshot capture success rate
- Tool execution counts
- Session durations
- Error rates by category

---

## 9. HACKATHON SUBMISSION CHECKLIST

### 9.1 DevPost Submission
```
□ Project title and tagline
□ Demo video (2-3 minutes)
□ Written description
□ Tech stack listed
□ Team members
□ Login credentials for judges:
    URL: https://proxi.audista.com
    Username: judge_demo
    Password: [secure password]
□ Test scenarios document
□ Architecture diagram
```

### 9.2 Judge Testing Instructions
```markdown
## Testing Proxi

### Prerequisites
- Mobile phone or desktop browser
- Stable internet connection

### Access
1. Navigate to https://proxi.audista.com
2. Login with provided credentials
3. Select "Sales Demo Workstation"

### Test Scenarios

**Scenario 1: System Information**
Say: "What is the current system time?"
Expected: Agent responds with current time

**Scenario 2: CRM Navigation**
Say: "Open the CRM application and find customer lifetime value"
Expected: Agent opens CRM, navigates tabs, reports $1.2M LTV

**Scenario 3: Screenshot Verification**
Say: "Send me a screenshot of the pricing tool"
Expected: Screenshot appears in chat showing pricing UI

**Scenario 4: File Discovery**
Say: "Find PowerPoint files in Downloads from last week"
Expected: Agent searches and reports found files

**Scenario 5: Document Creation**
Say: "Create a business case presentation using the brand template"
Expected: Agent creates PPT with slide content

### Notes
- The backend VM may take 1-2 minutes to wake if idle
- Voice commands require microphone permission
- Screenshots show actual Windows desktop state
```

---

## 10. COST ESTIMATES

### Always Free (Oracle Cloud)
| Resource | Usage | Cost |
|----------|-------|------|
| Ubuntu A1.Flex (1 OCPU, 6GB) | 24/7 | $0 |
| Block Storage (47GB) | Always | $0 |
| Outbound Data | 10TB/month | $0 |

### Pay-As-You-Go (Windows VM)
| Provider | Instance | Hourly | Monthly (24/7) |
|----------|----------|--------|----------------|
| GCP e2-medium + Windows | 2 vCPU, 4GB | $0.07 | ~$50 |
| Azure B2s + Windows | 2 vCPU, 4GB | $0.06 | ~$45 |
| Oracle E2.1.Standard | 1 OCPU, 8GB | $0.04 | ~$30 |

### Hackathon Strategy
- Use GCP $300 free credits
- Run Windows VM only during judging hours
- Auto-shutdown after 30 min idle
- **Estimated cost: $0-20 for 17-day judging period**

---

## 11. NEXT STEPS

### Immediate (Before Submission)
1. [ ] Implement authentication system
2. [ ] Create workstation registry UI
3. [ ] Deploy frontend to Oracle Ubuntu
4. [ ] Set up Windows VM on GCP
5. [ ] Configure Tailscale networking
6. [ ] Install Virtual Display Driver
7. [ ] Test full demo flow
8. [ ] Record demo video

### Post-Hackathon (If Winner)
1. [ ] Multi-user support
2. [ ] Proper IAM integration (OAuth, SAML)
3. [ ] Workstation auto-discovery
4. [ ] Mobile native app
5. [ ] Enterprise security audit
6. [ ] Kubernetes deployment option

---

*Document maintained by Proxi Development Team*
