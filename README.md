# Proxi: The Headless OS Operator

> **Work while you're on the move.** Control your desktop from your phone.

[![Google Gemini](https://img.shields.io/badge/Powered%20by-Google%20Gemini-4285F4?logo=google)](https://ai.google.dev/)
[![Python 3.12](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)](https://react.dev)

---

## What is Proxi?

Proxi is an **OS-level AI agent** that bridges high-level reasoning (Google Gemini) with low-level execution (Mouse/Keyboard/Vision). Unlike browser-only agents, Proxi can control **any application** on your desktop.

### Key Differentiators

| Feature | Browser Agents | Proxi |
|---------|---------------|-------|
| **Scope** | DOM manipulation only | Full OS control |
| **Legacy Apps** | ❌ | ✅ Notepad, Excel, VPNs |
| **System Control** | ❌ | ✅ Task Manager, Services |
| **Verification** | Trust LLM output | ✅ Independent audit |
| **Mobile Access** | Limited | ✅ Full telepresence |

---

## Quick Start

### Option 1: Windows (Recommended for Desktop Control)

```powershell
# 1. Clone the repository
git clone https://github.com/vermamanoj/proxi-ai.git
cd proxi-ai

# 2. Run setup (as Administrator)
.\setup_windows.ps1

# 3. Edit .env with your API key
notepad .env

# 4. Start the server
.\run_proxi.bat
```

### Option 2: Docker Compose (Recommended)

```bash
# 1. Clone and configure
git clone https://github.com/vermamanoj/proxi-ai.git
cd proxi-ai
cp .env.example .env
nano .env  # Add your GEMINI_API_KEY

# 2. Start all services (Core + Agent + Frontend)
docker-compose up -d

# 3. Check status
docker-compose ps
```

**Services:**
| Service | Port | Purpose |
|---------|------|---------|
| `core` | 4000 | Orchestration, LLM, Auth |
| `agent` | 4001 | Isolated tool execution |
| `frontend` | 4002 | React UI |

### Option 2b: Manual Docker (Individual Containers)

```bash
# Build images
docker build -t proxi-core -f backend/Dockerfile backend/
docker build -t proxi-agent -f backend/Dockerfile.agent backend/

# Run Core (needs API key)
docker run -d --name proxi-core -p 4000:8000 \
  -e GEMINI_API_KEY=your_key_here \
  proxi-core

# Run Agent (isolated, no API key needed)
docker run -d --name proxi-agent -p 4001:8081 proxi-agent

# Check logs
docker logs proxi-core --tail 20
```

### Option 3: Development Mode

```bash
# Backend (Core)
cd backend
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

---

## Configuration

Create a `.env` file in the project root:

```ini
# Required (Core only - Agent doesn't need this)
GEMINI_API_KEY=your_gemini_api_key_here

# Optional integrations
GITHUB_TOKEN=your_github_token_here
```

### Architecture (Security Split)

```
┌─────────────┐         ┌─────────────┐
│  PROXI CORE │───HTTP──│ PROXI AGENT │
│  Port 4000  │         │  Port 4001  │
├─────────────┤         ├─────────────┤
│ ✓ API Keys  │         │ ✗ No keys   │
│ ✓ User DB   │         │ ✗ No DB     │
│ ✓ LLM calls │         │ ✓ Tools only│
└─────────────┘         └─────────────┘
   SAFE ZONE            BLAST RADIUS
```

**Why?** If LLM tool execution is compromised, only Agent is affected. Core (with API keys, user data) stays safe.

---

## Features

### 🎯 Verifiable Agent (Triple Handshake)
Proxi never blindly trusts its own output. State-changing actions go through:
1. **Assign** - Define goal + verification criteria (process_killed, file_exists)
2. **Execute** - Run tools with transparency
3. **Verify** - Independent system check confirms actual state
4. **Judge** - Pass, retry, or escalate

### �️ Command Guard (Security Layer)
- Automatic approval gates for destructive commands (kill, delete, stop)
- Session-based approval tracking
- Blocked commands for dangerous operations

### �🖥️ Desktop Control (Ghost Mode)
- Mouse clicks, drags, scrolling
- Keyboard typing and hotkeys
- Screenshot + Vision analysis
- Windows UI automation
- Window management (focus, list, position)

### 📷 Image Upload + Action
- Upload images from mobile camera
- Agent can analyze AND take action on images
- Save uploaded images to desktop
- Staged upload UX (preview before submit)

### 📱 Mobile Telepresence
- Access via any browser
- Voice commands (Gemini Live)
- Real-time status streaming
- Works over Cloudflare Tunnel
- Session persistence (5-minute TTL for follow-ups)
- **Chat/Remote mode toggle** - Chat (voice only) vs Remote (desktop control)
- Mic and Speaker controls (separate toggles)
- Collapsible Mission panel with goal progress
- Collapsible tool outputs in chat
- Approval modal for destructive commands

### 📊 PowerPoint Automation
- Get/set active presentation
- Navigate, duplicate, delete slides
- Edit text shapes by name
- Create business documents on-the-fly

### 🔍 Transparency Protocol
The agent explains reasoning before every action:
```
Agent: "I will check system health to assess CPU usage..."
Tool:  get_system_health() → {'cpu_percent': 99.8}
Agent: "CPU critical. Identifying culprit process..."
Tool:  run_terminal_command("top") → ffmpeg at 99.8%
Agent: "Terminating ffmpeg to resolve spike..."
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  FRONTEND (React + Vite) - Port 4002                    │
│  ├── Voice Input (Gemini Live WebRTC)                  │
│  ├── Neural Trace (Real-time thought visualization)    │
│  ├── Agent Selector (switch target workstations)       │
│  └── Mission Control (Status dashboard)                │
└─────────────────────────────────────────────────────────┘
                          │ HTTPS/WebSocket
                          ▼
┌─────────────────────────────────────────────────────────┐
│  PROXI CORE (FastAPI) - Port 4000                       │
│  ├── GeminiService (AI orchestration, 45 tools)        │
│  ├── Orchestrator (Mission tracking, verification)     │
│  ├── Auth & Sessions (user management)                 │
│  └── Agent Proxy (routes tools to selected agent)      │
└─────────────────────────────────────────────────────────┘
                          │ HTTP /execute
                          ▼
┌─────────────────────────────────────────────────────────┐
│  PROXI AGENT (Isolated) - Port 4001                     │
│  ├── DesktopService (tool execution only)              │
│  ├── No API keys, No DB, No user data                  │
│  └── Blast radius limited if compromised               │
└─────────────────────────────────────────────────────────┘
```

---

## API Endpoints

### Core (Port 4000)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat` | POST | Send message, get streaming response |
| `/api/health` | GET | System health check |
| `/api/sessions` | GET/POST | Session management |
| `/api/workstations` | GET | List registered agents |
| `/api/workstations/{id}/activate` | POST | Set active agent for tools |
| `/api/workstations/deactivate` | POST | Use local execution |

### Agent (Port 4001)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Agent health status |
| `/execute` | POST | Execute a tool |
| `/capabilities` | GET | List available tools |

---

## Troubleshooting

### Backend won't start
```bash
# Check Python version (need 3.12+)
python --version

# Reinstall dependencies
pip install -r backend/requirements.txt
```

### "API Key Missing" error
- Ensure `.env` file exists in project root
- Check encoding (must be UTF-8, not UTF-16)
- Verify key format: `GEMINI_API_KEY=AIza...`

### Desktop control not working
- Windows: Run as Administrator
- Must be in interactive session (not SSH)
- Ensure agent is running and activated

### Frontend can't connect to backend
- Verify Core is running: `docker logs proxi-core`
- Check ports: Core=4000, Agent=4001, Frontend=4002
- Try `http://localhost:4000/api/health` directly

---

## Documentation

- [BLUEPRINT.md](./BLUEPRINT.md) - System architecture deep dive
- [USER_GUIDE.md](./USER_GUIDE.md) - Comprehensive usage guide

---

## License

MIT License - See [LICENSE](./LICENSE) for details.

---

## Acknowledgments

Built for the **Google Gemini Hackathon** using:
- [Google Gemini API](https://ai.google.dev/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [React](https://react.dev/)
- [PyAutoGUI](https://pyautogui.readthedocs.io/)
