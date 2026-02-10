# 01 — Product Overview

## What is Proxi?

Proxi is a **Headless OS-Level AI Agent** — a system that gives users full control over Windows and Linux desktops from any device (phone, tablet, laptop) through a conversational AI interface powered by Google Gemini.

Unlike browser-only automation tools that manipulate the DOM, Proxi operates at the **operating system level**: it can click, type, read screens, run terminal commands, automate PowerPoint, manage processes, and verify its own work — all through natural language.

## Core Value Proposition

| Differentiator | Description |
|----------------|-------------|
| **OS-Level Control** | Full desktop automation (mouse, keyboard, screenshots, window management) — not limited to browser |
| **Mobile-First** | Control a remote Windows workstation from your phone |
| **Verifiable Agent** | Proves work was done correctly via Triple Handshake verification before reporting success |
| **Security-First** | Split architecture isolates LLM orchestration from desktop execution; command guardrails prevent dangerous operations |
| **Multi-Agent** | Connect to multiple workstations (Linux containers, Windows VMs) and switch between them |

## Target Users

- **IT Administrators** — Remote system diagnostics, incident response, process management
- **Sales Teams** — CRM lookups, pricing analysis, PowerPoint deck generation from phone
- **Security Analysts** — Forensic investigation, evidence collection, attack path visualization
- **General Knowledge Workers** — Desktop automation, file management, application control

## Tech Stack

### Backend
| Component | Technology | Version |
|-----------|------------|---------|
| API Framework | FastAPI | 0.109+ |
| ASGI Server | Uvicorn | 0.27+ |
| AI Models (LLM) | Gemini 3 Flash / Pro Preview | generativeai SDK 0.8+ |
| Database | SQLite (WAL mode) | Built-in |
| Auth | bcrypt + session cookies | bcrypt 4.1 |
| Desktop Automation | PyAutoGUI + PyWinAuto | 0.9.54 / 0.6.8 |
| Vision | OpenCV + Set-of-Mark overlay | 4.9+ |
| System Monitoring | psutil | 5.9+ |

### Frontend
| Component | Technology |
|-----------|------------|
| Framework | React 18 + TypeScript |
| Build Tool | Vite |
| Styling | Tailwind CSS |
| Voice | Gemini 2.5 Live Native Audio (WebRTC) |
| Mobile | Capacitor (Android wrapper) |

### Infrastructure
| Component | Technology |
|-----------|------------|
| Containerization | Docker + docker compose |
| Reverse Proxy | Nginx |
| Networking | Tailscale (mesh VPN for remote agents) |
| Cloud | Oracle Cloud (Ubuntu) for Core + Frontend |

## Feature Inventory

### Implemented (Production-Ready)
- 48+ tools (system, desktop, PPT, integrations, evidence, missions)
- Multi-turn conversational AI with streaming SSE responses
- Session persistence with history management
- Authentication (password + magic links for judges)
- Workstation registry with health monitoring
- Command approval flow with guardrails
- Screenshot sharing in chat
- Image upload + action execution
- Mission tracking with Triple Handshake verification
- Mobile-first chat UI
- Voice I/O via Gemini Live WebRTC
- Demo mode with simulated incidents
- Four execution modes (plan/quick/balanced/thorough)
- Modular system prompt assembly
- Evidence on Demand for forensic investigations
- Attack path Mermaid diagram generation
- PowerPoint COM automation (20+ operations)

### In Progress
- Multi-tier cloud deployment
- Enhanced approval UI (modal with countdown)
- Escalate-to-Human UI integration

### Planned
- Landing page (public, no auth)
- Headless operation (Virtual Display Driver)
- On-demand VM startup
- Mock Apps Flask server for demos

## Repository Structure

```
proxi-ai/
├── backend/                    # Python backend (Core + Agent)
│   ├── main.py                 # FastAPI Core server (980 lines)
│   ├── agent_server.py         # FastAPI Agent server (679 lines)
│   ├── database.py             # SQLite persistence
│   ├── auth/                   # Authentication service
│   ├── config/                 # Modes + prompt modules
│   │   ├── modes.json
│   │   └── prompts/            # System prompt .md files
│   ├── models/                 # Pydantic API models
│   ├── registry/               # Workstation registry
│   ├── services/
│   │   ├── gemini_service.py   # Core AI orchestrator (1933 lines)
│   │   ├── orchestrator.py     # Triple Handshake missions
│   │   ├── agent_proxy.py      # Core→Agent HTTP proxy
│   │   └── desktop/            # Desktop service implementations
│   ├── tools/                  # Tool definitions
│   │   ├── command_guard.py    # Security guardrails
│   │   ├── ppt_tools.py        # PowerPoint COM automation
│   │   └── standard_tools.py   # Productivity + system tools
│   └── utils/                  # Logging utilities
├── frontend/                   # React + Vite SPA
├── demo-apps/                  # CRM and Pricing demo apps
├── scripts/                    # Deployment + setup scripts
├── deploy/                     # Nginx config
├── proxi_docs/                 # This documentation
└── docker-compose.yml          # Container orchestration
```

## Key Metrics

| Metric | Value |
|--------|-------|
| Backend source files | 18 Python files |
| Total backend lines | ~7,800 |
| Tool count | 48+ |
| Prompt modules | 7 markdown files |
| Desktop service implementations | 5 (Real, Linux, Proxy, Null, Mock) |
| API endpoints | 25+ REST + SSE |
| Execution modes | 4 (plan, quick, balanced, thorough) |

---

*Next: [Architecture →](02_architecture.md)*
