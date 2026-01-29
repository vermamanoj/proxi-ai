# Proxi Deployment & Operations

**Version:** v3.0.0  
**Last Updated:** January 28, 2026

---

## 1. Quick Start (Production Deployment Script)

```bash
# Clone and configure
git clone https://github.com/vermamanoj/proxi-ai.git
cd proxi-ai
cp .env.example .env
# Edit .env with your GEMINI_API_KEY and PROXI_AGENT_KEY

# Run the full deployment script
./deploy.sh

# Check service status
./deploy.sh --status

# View logs
./deploy.sh --logs
```

### Deploy Script Options

| Command | Description |
|---------|-------------|
| `./deploy.sh` | Full deployment (pull + docker + nginx) |
| `./deploy.sh --docker` | Rebuild and restart Docker containers only |
| `./deploy.sh --nginx` | Update nginx config and reload |
| `./deploy.sh --pull` | Git pull latest code |
| `./deploy.sh --logs` | View container logs (follow mode) |
| `./deploy.sh --status` | Check all service status |
| `./deploy.sh --restart` | Restart containers without rebuild |
| `./deploy.sh --help` | Show all options |

### Services Started

| Service | Port | Purpose |
|---------|------|---------|
| `core` | 4000 | Orchestration, LLM, Auth |
| `agent` | 4001 | Isolated tool execution |
| `frontend` | 4002 | React UI |

---

## 2. Environment Configuration

### Required Variables

```ini
# .env file in project root
GEMINI_API_KEY=your_gemini_api_key_here

# For voice support in frontend
VITE_GEMINI_API_KEY=your_gemini_api_key_here
```

### Optional Variables

```ini
# Integrations
GITHUB_TOKEN=your_github_token_here
SLACK_WEBHOOK_URL=https://hooks.slack.com/...

# Tailscale (for remote agents)
TAILSCALE_AUTHKEY=tskey-auth-xxxxxxxxxxxxx

# Agent authentication (generate with: openssl rand -hex 32)
PROXI_AGENT_KEY=your_strong_64_char_hex_key_here
```

### Security: Set .env Permissions

**On Linux server (production):**
```bash
# Restrict .env to owner read/write only
chmod 600 .env

# Verify permissions (should show -rw-------)
ls -la .env
```

> ⚠️ **Important:** Never commit `.env` to git. It contains secrets.

---

## 2.1 User Credentials

On first run, Proxi generates random passwords for default users (`demo`, `judge`, `admin`). These are saved to:
- `backend/auth/users.json` (hashed passwords)
- `backend/auth/INITIAL_CREDENTIALS.txt` (plaintext, delete after noting)

### Setting Custom Passwords

Run from project root on the **host machine** (not inside Docker):

```bash
# Set password for each user
python3 scripts/set_password.py demo YourDemoPassword
python3 scripts/set_password.py admin YourAdminPassword
python3 scripts/set_password.py judge YourJudgePassword

# Restart core for changes to take effect
docker compose restart core
```

**Mobile-friendly password tips:**
- Use 8+ characters
- Avoid symbols that require keyboard switching (e.g., `@#$%`)
- Good: `ProxiDemo2026`, `JudgeAccess42`

### Resetting All Credentials

```bash
# Delete users file and restart - new random passwords will be generated
rm backend/auth/users.json
docker compose restart core
docker logs proxi-ai-core-1 | head -30  # View new passwords
```

---

## 3. Docker Commands

```powershell
# Start all services
docker compose up -d

# Rebuild after code changes
docker compose up -d --build

# View logs
docker compose logs -f
docker compose logs core --tail 50

# Stop all services
docker compose down

# Restart specific service
docker compose restart core

# Enter container shell
docker compose exec core bash
docker compose exec frontend sh
```

---

## 4. Health Checks

```powershell
# Core API
Invoke-WebRequest -Uri http://localhost:4000/api/workstations -UseBasicParsing

# Agent health
Invoke-WebRequest -Uri http://localhost:4001/health -UseBasicParsing

# Frontend
# Open http://localhost:4002 in browser
```

---

## 5. Remote Agent Setup (Tailscale)

For agents behind NAT/firewall, use Tailscale mesh VPN.

### Install Tailscale

**Linux:**
```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up --authkey=tskey-auth-xxxxxxxxxxxxx
tailscale ip -4  # Note the 100.x.x.x IP
```

**Windows:**
```powershell
winget install Tailscale.Tailscale
# Login via system tray → Google SSO
tailscale status
```

### Register Remote Agent

```bash
curl -X POST http://core-server:4000/api/workstations \
  -H "Content-Type: application/json" \
  -d '{
    "id": "win-remote",
    "name": "Windows Desktop",
    "host": "100.64.0.2",
    "port": 8081,
    "workstation_type": "windows"
  }'
```

---

## 6. Windows Agent Deployment

The Windows agent runs separately from Core for desktop automation.

### Setup Script

```powershell
# Clone to separate directory
git clone https://github.com/vermamanoj/proxi-ai.git C:\proxi-win-agent
cd C:\proxi-win-agent\backend

# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run agent (no API key needed)
uvicorn backend.agent_server:app --host 0.0.0.0 --port 8081
```

### Run as Windows Service (Optional)

```powershell
# Install NSSM
choco install nssm -y

# Create service
nssm install ProxiAgent "C:\proxi-win-agent\venv\Scripts\python.exe" "-m uvicorn backend.agent_server:app --host 0.0.0.0 --port 8081"
nssm set ProxiAgent AppDirectory "C:\proxi-win-agent"
nssm start ProxiAgent
```

---

## 7. Production Nginx Config

```nginx
server {
    listen 80;
    server_name proxi.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name proxi.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/proxi.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/proxi.yourdomain.com/privkey.pem;

    # Frontend
    location / {
        proxy_pass http://localhost:4002;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:4000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 300s;
    }
}
```

---

## 8. Troubleshooting

### Container Won't Start
```powershell
docker compose logs core
docker compose down
docker compose up -d --build
```

### Port Already in Use
```powershell
netstat -ano | findstr :4000
taskkill /PID <pid> /F
```

### Database Locked
- SQLite uses WAL mode by default
- If issues persist, stop containers and delete `backend/proxi.db`

### Agent Shows Offline
- Check agent health: `curl http://agent-ip:8081/health`
- Verify network connectivity between Core and Agent
- Check firewall rules

### Agent Returns 401 Unauthorized

**Root Cause:** The `PROXI_AGENT_KEY` must be set in `.env` and passed to both `core` and `agent` containers.

**Architecture Note:** There are TWO code paths that call the agent:
1. `agent_proxy.py` - Used for direct API calls (health checks, activation)
2. `proxy_adapter.py` - Used by GeminiService for LLM tool execution

Both must include the `X-Agent-Key` header.

**Fix Checklist:**
```powershell
# 1. Verify .env has the key
grep PROXI_AGENT_KEY .env

# 2. Check docker-compose.yml passes it to both services
# environment:
#   - PROXI_AGENT_KEY=${PROXI_AGENT_KEY}

# 3. Rebuild containers (env vars are read at container start)
docker compose down
docker compose up -d --build

# 4. Verify key is loaded in container
docker compose exec core python -c "import os; print(os.environ.get('PROXI_AGENT_KEY', 'NOT_SET'))"

# 5. Test agent directly with header
docker compose exec core python -c "import requests; r = requests.post('http://agent:8081/execute', json={'tool_name': 'get_system_health', 'parameters': {}}, headers={'X-Agent-Key': 'YOUR_KEY'}); print(r.status_code)"
```

**Key Files:**
- `backend/services/desktop/proxy_adapter.py` - Must have `X-Agent-Key` header
- `backend/services/agent_proxy.py` - Must have `X-Agent-Key` header  
- `backend/agent_server.py` - Validates the header

---

## 9. Backup & Recovery

### Database Backup
```powershell
# Copy SQLite database
docker cp proxi-ai-core-1:/app/proxi.db ./backup/proxi.db

# Copy user data
docker cp proxi-ai-core-1:/app/auth/users.json ./backup/users.json
```

### Restore
```powershell
docker cp ./backup/proxi.db proxi-ai-core-1:/app/proxi.db
docker compose restart core
```

---

*For architecture details, see [ARCHITECTURE.md](./ARCHITECTURE.md)*  
*For usage guide, see [USER_GUIDE.md](../USER_GUIDE.md)*
