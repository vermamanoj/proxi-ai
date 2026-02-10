# 09 — Deployment

## Overview

Proxi deploys as three separate services: Frontend, Core, and Agent(s). Each has its own Dockerfile, requirements, and configuration. Services communicate over HTTP within a Docker network or via Tailscale for remote agents.

---

## Environment Overview

| Environment | OS | Purpose | Location |
|-------------|-----|---------|----------|
| **Development** | Windows 11 | Coding, testing, local agent | `E:\data\proxi-ai` (dev repo) |
| **Windows Agent** | Windows 11 | Desktop automation, PPT, GUI | `E:\data\proxi-win-agent` (separate clone) |
| **Production** | Ubuntu Linux (Oracle Cloud) | Frontend + Core + Linux Agent containers | Docker Compose on cloud VM |

> Development runs Docker Desktop on Windows. Production runs native Docker on Ubuntu. The Windows agent always runs natively (not in Docker) since it needs GUI access.

---

## Docker Compose (Development / Demo)

### `docker-compose.yml`

```yaml
services:
  frontend:
    build: ./frontend
    ports:
      - "4002:5173"
    depends_on:
      - core

  core:
    build: ./backend
    ports:
      - "4000:8000"
    volumes:
      - ./data:/app/data          # SQLite persistence
      - ./.env:/app/.env          # Environment variables
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - PROXI_AGENT_KEY=${PROXI_AGENT_KEY}

  agent:
    build:
      context: ./backend
      dockerfile: Dockerfile.agent
    ports:
      - "4001:8081"
    environment:
      - PROXI_AGENT_KEY=${PROXI_AGENT_KEY}
```

### Port Mapping

| Service | Container Port | Host Port | URL |
|---------|---------------|-----------|-----|
| Frontend | 5173 | 4002 | `http://localhost:4002` |
| Core | 8000 | 4000 | `http://localhost:4000` |
| Linux Agent | 8081 | 4001 | `http://localhost:4001` |

---

## Dockerfiles

### Core (`backend/Dockerfile`)

```dockerfile
FROM python:3.12-slim
WORKDIR /app

# System deps + gosu for user switching
RUN apt-get update && apt-get install -y gcc procps curl gosu

# Non-root user
RUN groupadd -r proxi && useradd -r -g proxi proxi

# Linux-specific requirements (no Windows packages)
COPY requirements-linux.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Data directory for SQLite
RUN mkdir -p /app/data && chown proxi:proxi /app/data

# Application code
COPY . /app/backend

# Entrypoint fixes permissions, switches to proxi user
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENV PYTHONPATH=/app
EXPOSE 8000
ENTRYPOINT ["/app/entrypoint.sh"]
```

**Entrypoint** (`entrypoint.sh`):
```bash
#!/bin/bash
# Fix ownership of mounted volumes (runs as root)
chown -R proxi:proxi /app/data 2>/dev/null || true
chown -R proxi:proxi /app/backend/auth 2>/dev/null || true
chown -R proxi:proxi /app/backend/registry 2>/dev/null || true
mkdir -p /app/data && chmod 755 /app/data

# Switch to non-root user and start
exec gosu proxi uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### Agent (`backend/Dockerfile.agent`)

```dockerfile
FROM python:3.12-slim
WORKDIR /app

RUN apt-get update && apt-get install -y gcc python3-dev procps curl

# Non-root user
RUN groupadd -r proxi && useradd -r -g proxi proxi

# Minimal requirements
COPY requirements-agent.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy ONLY what the agent needs (no auth, no database, no gemini service)
COPY services/desktop /app/backend/services/desktop
COPY tools /app/backend/tools
COPY utils /app/backend/utils
COPY agent_server.py /app/backend/agent_server.py

# Create __init__.py files for Python imports
RUN mkdir -p /app/backend/services /app/backend/tools /app/backend/utils && \
    touch /app/backend/__init__.py /app/backend/services/__init__.py \
          /app/backend/tools/__init__.py /app/backend/utils/__init__.py

USER proxi
EXPOSE 8081
CMD ["python", "-m", "uvicorn", "backend.agent_server:app", "--host", "0.0.0.0", "--port", "8081"]
```

**Key difference**: Agent Dockerfile copies only desktop services, tools, and utils — no auth, no database, no gemini_service, no main.py. This enforces security isolation at the build level.

---

## Requirements Files

### `requirements.txt` (Windows Development — Full Stack)

```
fastapi==0.109.0
uvicorn==0.27.0
gunicorn==21.2.0
pydantic==2.6.0
python-dotenv==1.0.1
google-generativeai>=0.8.0
python-multipart==0.0.9
PyGithub==2.1.1
psutil==5.9.8
pyautogui==0.9.54
easyocr==1.7.1
opencv-python-headless==4.9.0.80
pillow==10.2.0
numpy==1.26.4
pywinauto==0.6.8
comtypes==1.2.0
pywin32==306
pyperclip==1.8.2
requests==2.31.0
bcrypt==4.1.2
```

### `requirements-linux.txt` (Core Container)

Excludes all Windows-specific and GUI packages:
- No `pyautogui` (requires display)
- No `easyocr` (heavy, terminal-only agent doesn't need it)
- No `opencv-python-headless` (not needed for Core)
- No `pywinauto`, `comtypes`, `pywin32` (Windows only)
- Adds `aiohttp` for async agent communication

### `requirements-agent.txt` (Agent — Windows or Linux)

Minimal deps for the agent server:
- Core API: `fastapi`, `uvicorn`, `pydantic`
- System: `psutil`, `python-dotenv`
- HTTP: `httpx`, `requests`
- Screenshot: `mss`, `Pillow`, `opencv-python`, `numpy`
- Desktop: `pyautogui`, `pyperclip`
- Windows-only (conditional): `pywinauto`, `pywin32`
- Optional: `google-generativeai` (for local `/ground` endpoint)

---

## Environment Variables

### Required

| Variable | Service | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | Core | Google Gemini API key for LLM access |

### Recommended

| Variable | Service | Description |
|----------|---------|-------------|
| `PROXI_AGENT_KEY` | Core + Agent | Shared secret for Core ↔ Agent authentication |

### Optional

| Variable | Service | Default | Description |
|----------|---------|---------|-------------|
| `PROXI_DEV_MODE` | Core | `false` | Auto-approve sensitive commands (dev only) |
| `GITHUB_TOKEN` | Core | — | GitHub API access for integration tools |
| `CORS_ORIGINS` | Core | localhost | Comma-separated allowed CORS origins |
| `GEMINI_API_KEY` | Agent | — | Enables local visual grounding `/ground` endpoint |
| `RUNTIME_MODE` | Core | — | Legacy: `DEMO` for MockDesktopService |

### `.env` File Template

```env
# Required
GEMINI_API_KEY=your_gemini_api_key_here

# Recommended
PROXI_AGENT_KEY=your_shared_agent_secret_here

# Optional
PROXI_DEV_MODE=false
GITHUB_TOKEN=ghp_your_github_token
CORS_ORIGINS=http://localhost:4002,https://proxi.yourdomain.com
```

---

## Windows Agent (Native)

For Windows desktop automation, the agent runs natively (not in Docker) since it needs access to the Windows GUI, COM automation, and display.

### Setup

```powershell
# Clone the agent repo (separate from dev repo)
cd E:\data\proxi-win-agent

# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r backend\requirements-agent.txt

# Create .env
echo "PROXI_AGENT_KEY=your_shared_secret" > .env
echo "GEMINI_API_KEY=your_key_for_grounding" >> .env
```

### Run

```powershell
# From the repo root
python -m uvicorn backend.agent_server:app --host 0.0.0.0 --port 8081
```

### Register with Core

The Windows agent must be registered in the workstation registry:

**Option A**: Add to `backend/registry/workstations.json`:
```json
{
  "win-desktop": {
    "id": "win-desktop",
    "name": "Windows Desktop",
    "description": "Windows Server with desktop automation",
    "workstation_type": "windows",
    "host": "100.64.0.2",
    "port": 8081,
    "capabilities": ["desktop_automation", "screenshot", "browser", "powerpoint"],
    "status": "unknown",
    "tags": ["windows", "desktop"]
  }
}
```

**Option B**: Via API:
```bash
curl -X POST http://localhost:4000/api/workstations \
  -H "Content-Type: application/json" \
  -d '{"id": "win-desktop", "name": "Windows Desktop", "host": "100.64.0.2", "port": 8081, ...}'
```

### Networking

For remote Windows agents, use **Tailscale** for secure mesh VPN:
1. Install Tailscale on both Core server and Windows agent machine
2. Use Tailscale IP (100.x.y.z) as the agent `host`
3. No port forwarding or firewall rules needed

For local Docker → Windows host:
- Use `host.docker.internal` as the agent host (Docker Desktop)
- Or the machine's LAN IP

---

## Production Deployment

### Multi-Machine Topology

```
Oracle Cloud VM (Ubuntu)              Windows Server
├── Frontend container :4002          ├── Windows Agent :8081
├── Core container :4000              │   (native, not containerized)
├── Linux Agent container :4001       │
└── Nginx reverse proxy :80/:443     └── Connected via Tailscale
```

### Nginx Configuration

```nginx
# deploy/proxi.conf
server {
    listen 80;
    server_name proxi.yourdomain.com;

    # Frontend
    location / {
        proxy_pass http://localhost:4002;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Core API
    location /api/ {
        proxy_pass http://localhost:4000;
        proxy_http_version 1.1;
        proxy_set_header Connection '';
        proxy_buffering off;              # Required for SSE
        proxy_cache off;
        proxy_read_timeout 120s;          # Long timeout for thorough mode
    }
}
```

**Critical SSE settings**: `proxy_buffering off` and `proxy_cache off` are required for streaming chat responses.

### Deployment Scripts

| Script | Purpose |
|--------|---------|
| `scripts/deploy-core.ps1` | Build and deploy Core container |
| `scripts/deploy-frontend.ps1` | Build and deploy Frontend container |
| `scripts/deploy-agent-windows.ps1` | Setup Windows agent service |
| `scripts/deploy-agent-linux.sh` | Build and deploy Linux agent container |

### Health Monitoring

Check service health:

```bash
# Core
curl http://localhost:4000/health

# Linux Agent
curl -H "X-Agent-Key: $PROXI_AGENT_KEY" http://localhost:4001/health

# Windows Agent
curl -H "X-Agent-Key: $PROXI_AGENT_KEY" http://100.64.0.2:8081/health

# All agents via Core
curl http://localhost:4000/api/workstations/health-all
```

---

## Build Commands

### Full Stack (Docker Compose)

```bash
# Build all services
docker compose build

# Start all services
docker compose up -d

# View logs
docker compose logs -f core
docker compose logs -f agent

# Rebuild single service
docker compose build core
docker compose up -d core
```

### Individual Services

```bash
# Core
docker build -t proxi-core -f backend/Dockerfile backend/
docker run -p 4000:8000 --env-file .env proxi-core

# Agent
docker build -t proxi-agent -f backend/Dockerfile.agent backend/
docker run -p 4001:8081 -e PROXI_AGENT_KEY=secret proxi-agent

# Frontend
docker build -t proxi-frontend frontend/
docker run -p 4002:5173 proxi-frontend
```

---

## Data Persistence

### Volumes to Back Up

| Path | Content | Criticality |
|------|---------|-------------|
| `data/proxi.db` | Chat sessions, missions, images | High |
| `backend/auth/users.json` | User accounts + password hashes | High |
| `backend/auth/sessions.json` | Active auth sessions | Medium |
| `backend/auth/magic_links.json` | Magic link tokens | Medium |
| `backend/registry/workstations.json` | Agent registrations | Low (recreatable) |
| `.env` | API keys and secrets | Critical |

### First Run

On first start with no existing data:
1. SQLite database created automatically
2. Default users generated with random passwords (printed to stdout)
3. Credentials saved to `backend/auth/INITIAL_CREDENTIALS.txt`
4. Demo workstations created in registry
5. **Delete `INITIAL_CREDENTIALS.txt` after noting passwords**

---

*Previous: [Database ←](08_database.md) | Next: [Developer Guide →](10_developer_guide.md)*
