# Proxi — Verified Execution for Real Computers

> **Proxi executes real work on real systems — safely, verifiably, and under human control.**
>
> *When APIs don't exist and trust still matters.*

[![Google Gemini](https://img.shields.io/badge/Powered%20by-Gemini%203-4285F4?logo=google)](https://ai.google.dev/)
[![Python 3.12](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)](https://react.dev)
[![Live Demo](https://img.shields.io/badge/Live-proxi.audista.com-green)](https://proxi.audista.com)

---

## The Problem

**AI can reason. Execution still happens behind keyboards.**

AI assistants stop at suggestions. They tell you *what* to do, but you still have to do it yourself — navigate apps, click buttons, copy data between tools. Especially with legacy systems that have no APIs.

## The Solution

**Command from your phone. Execute on your desktop. Stay in control.**

Proxi navigates real desktop apps, browsers, and terminals — including legacy systems without APIs. It executes multi-step workflows end-to-end and proves completion with visual evidence.

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              📱 YOUR PHONE                                  │
│                     Voice Commands / Text / Image Upload                    │
└────────────────────────────────────┬───────────────────────────────────────┘
                                     │ HTTPS
                                     ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                        ⚡ PROXI CORE (Port 4000)                            │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐            │
│  │  🧠 Gemini 3    │  │  🔐 Auth &      │  │  📋 Mission     │            │
│  │  Orchestration  │  │  Sessions       │  │  Tracking       │            │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘            │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐            │
│  │  🛡️ Command     │  │  🔀 Agent       │  │  ✅ Verifiable  │            │
│  │  Guard          │  │  Router         │  │  Agent          │            │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘            │
│                           SAFE ZONE (API Keys, User Data)                  │
└────────────────────────────────────┬───────────────────────────────────────┘
                                     │ HTTP /execute
                    ┌────────────────┴────────────────┐
                    ▼                                 ▼
┌───────────────────────────────┐   ┌───────────────────────────────┐
│   🐧 LINUX AGENT (Port 4001) │   │   🪟 WINDOWS AGENT (Port 8081)│
│   Terminal / Git / Docker     │   │   Desktop / Office / CRM      │
│   DevOps / Python             │   │   Legacy Apps / GUI Automation│
│   ISOLATED (No Keys, No DB)  │   │   ISOLATED (No Keys, No DB)  │
└───────────────────────────────┘   └───────────────────────────────┘
```

**Security Split:** Core holds all secrets. Agents execute tools in isolation. If an agent is compromised, Core (with API keys, user data) stays safe.

---

## 🛡️ Trust by Design

Most agents claim success. **Proxi proves it.**

### Verified Execution
- 📸 **Screenshots as evidence** — visual proof of completed actions
- 📱 **Visual confirmation on your phone** — see results before marking complete
- ❌ **No "agent said it worked"** — independent verification via Triple Handshake

### Safety & Control (Command Guard)

| Level | Behavior | Examples |
|-------|----------|----------|
| 🟢 **Safe** | Auto-allowed | `list_files`, `get_screenshot`, `read_file` |
| 🟡 **Sensitive** | Human approval required | `delete_file`, `stop_service`, `run_command` |
| 🔴 **Blocked** | Never executed | `format`, `rm -rf /`, `shutdown` |

> *"Proxi never decides success. Reality does."*

---

## 🧠 Why Gemini Changes Everything

No hardcoded scripts. No brittle selectors. Proxi reasons through what it sees.

| Capability | How It Works |
|-----------|-------------|
| **Multimodal Vision** | Reads live screenshots like a human — understands UI layout, text, error messages |
| **On-the-Fly Reasoning** | Decides next action based on visual feedback. Adapts when UIs change |
| **Native Function Calling** | Executes desktop tools via Gemini's native tool-use. No LangChain wrappers |
| **Long Context Memory** | Maintains full workflow history across complex multi-step tasks |

---

## 💡 OS-Aware Intelligence

Proxi understands the state of your machine.

| State | Capability |
|-------|------------|
| 🔓 **Desktop Unlocked** | Full UI control — mouse, keyboard, apps |
| 🔒 **Desktop Locked** | Terminal fallback — commands still work |

**Share files both ways** — send screenshots from your phone to the desktop, receive results and exports back.

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| **Mobile-First Control** | Control your office machine from your phone |
| **Voice Commands** | Real-time via Gemini Live Native Audio (WebRTC) |
| **48+ Tools** | System, desktop, PowerPoint, charts, SmartArt |
| **Multi-Workstation** | Switch between Windows/Linux agents |
| **Session Persistence** | Pick up where you left off |
| **Transparency Protocol** | Agent explains reasoning before every action |
| **Image Upload + Action** | Send photos from mobile, agent analyzes AND acts |
| **SOC Forensics** | Multi-platform security investigation simulation |

---

## Key Differentiators

| Feature | Browser Agents | Proxi |
|---------|---------------|-------|
| **Scope** | DOM manipulation only | Full OS control |
| **Legacy Apps** | ❌ | ✅ Notepad, Excel, VPNs |
| **System Control** | ❌ | ✅ Task Manager, Services |
| **Verification** | Trust LLM output | ✅ Independent audit |
| **Mobile Access** | Limited | ✅ Full telepresence |

---

## 🎯 Real-World Inspiration

The idea came from real moments — like negotiating pricing in a meeting without a laptop, knowing the data was sitting on a computer back at the office.

---

## Quick Start

### Docker Compose (Recommended)

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
| `agent` | 4001 | Isolated tool execution (Linux) |
| `frontend` | 4002 | React UI |

### Windows Development

```powershell
# 1. Clone the repository
git clone https://github.com/vermamanoj/proxi-ai.git
cd proxi-ai

# 2. Run setup (as Administrator)
.\setup_windows.ps1

# 3. Edit .env with your API key
notepad .env

# 4. Start backend
cd backend
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000

# 5. Start frontend (separate terminal)
cd frontend
npm install
npm run dev
```

### Configuration

Create a `.env` file in the project root (see `.env.example`):

```ini
# Required
GEMINI_API_KEY=your_gemini_api_key_here

# Agent authentication
PROXI_AGENT_KEY=your_shared_secret_here

# Optional
GITHUB_TOKEN=your_github_token_here
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
| `/api/workstations/{id}/activate` | POST | Set active agent |
| `/api/vision` | POST | Screenshot + vision analysis |
| `/api/files/upload` | POST | Upload file to agent |
| `/api/files/download` | POST | Download file from agent |

### Agent (Port 4001/8081)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Agent health status |
| `/execute` | POST | Execute a tool |
| `/capabilities` | GET | List available tools |
| `/ground` | POST | Visual grounding (Windows only) |

---

## Documentation

Comprehensive documentation is in the [`proxi_docs/`](./proxi_docs/) folder:

| Document | Description |
|----------|-------------|
| [Overview](./proxi_docs/01_overview.md) | Project summary, tech stack, value proposition |
| [Architecture](./proxi_docs/02_architecture.md) | Security-first split design, component flow |
| [Backend Services](./proxi_docs/03_backend_services.md) | Core services, Gemini orchestration |
| [Agent System](./proxi_docs/04_agent_system.md) | Agent protocol, desktop services, proxy pattern |
| [Tools Reference](./proxi_docs/05_tools_reference.md) | All 48+ tools with parameters |
| [Security](./proxi_docs/06_security.md) | Auth, command guard, threat model |
| [Prompt Engineering](./proxi_docs/07_prompt_engineering.md) | Modular prompts, modes, model config |
| [Database](./proxi_docs/08_database.md) | SQLite schema, sessions, missions |
| [Deployment](./proxi_docs/09_deployment.md) | Docker, production, Windows agent setup |
| [Developer Guide](./proxi_docs/10_developer_guide.md) | Contributing, code structure, conventions |
| [Additional Context](./proxi_docs/11_additional_context.md) | Project history, evolution, decisions |

Also see:
- [User Guide](./USER_GUIDE.md) — End-user usage instructions
- [Deployment Guide](./DEPLOYMENT.md) — Detailed production deployment
- [Changelog](./CHANGELOG.md) — Version history

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| **Backend won't start** | Check Python 3.12+: `python --version`. Reinstall: `pip install -r backend/requirements.txt` |
| **"API Key Missing"** | Ensure `.env` exists in root, UTF-8 encoding, format: `GEMINI_API_KEY=AIza...` |
| **Desktop control not working** | Windows: Run as Administrator. Must be interactive session (not SSH). |
| **Frontend can't connect** | Check ports: Core=4000, Agent=4001, Frontend=4002. Try `http://localhost:4000/api/health` |
| **Agent 401 Unauthorized** | Ensure `PROXI_AGENT_KEY` matches between Core and Agent `.env` files |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **AI** | Gemini 3 Flash/Pro Preview, Vision, Native Audio |
| **Backend** | Python 3.12, FastAPI, google-generativeai SDK |
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS |
| **Desktop** | PyAutoGUI, PyWinAuto, psutil |
| **Voice** | Gemini 2.5 Live Native Audio (WebRTC) |
| **Database** | SQLite (sessions, missions, evidence) |
| **Deployment** | Docker Compose, Nginx, Cloudflare |

---

## License

MIT License — See [LICENSE](./LICENSE) for details.

---

## Acknowledgments

Built for the **Google Gemini Hackathon** using:
- [Google Gemini API](https://ai.google.dev/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [React](https://react.dev/)
- [PyAutoGUI](https://pyautogui.readthedocs.io/)

**Supports Windows and Linux systems deployed on your infrastructure. Built for real-world constraints.**
