# Proxi System Architecture

**Version:** v3.0.0  
**Last Updated:** January 28, 2026

---

## 1. Overview

Proxi is a **Headless OS-Level AI Agent** that bridges high-level reasoning (Google Gemini) with low-level execution (Mouse/Keyboard/Vision) to automate tasks across Legacy Apps, Browsers, and Systems.

### Core Value Proposition
- Control Windows/Linux desktop from your phone
- Full OS control, not just browser DOM manipulation
- **Verifiable Agent** - proves it fixed issues before reporting success
- Works with legacy apps (Notepad, Excel, SAP-like systems)

---

## 2. Security-First Split Architecture

Proxi uses a security-focused split where sensitive data (API keys, user DB) stays in Core while tool execution happens in isolated Agents.

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
│        │  LINUX AGENT (4001)    │          │  WINDOWS AGENT (8081)   │    │
│        │  Docker Container      │          │  Separate Server        │    │
│        │  ✗ No API Keys         │          │  ✗ No API Keys          │    │
│        │  ✗ No User Data        │          │  ✗ No User Data         │    │
│        │  ✓ Tool Execution Only │          │  ✓ Desktop Automation   │    │
│        └─────────────────────────┘          └─────────────────────────┘    │
│              BLAST RADIUS                         BLAST RADIUS             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Security Benefit:** If LLM tool execution is compromised, only the Agent is affected. Core (with API keys, user data) remains isolated.

---

## 3. Component Responsibilities

| Component | Port | Purpose | Has API Keys? |
|-----------|------|---------|---------------|
| **Frontend** | 4002 | React UI, Agent Selector, Voice I/O | No |
| **Proxi Core** | 4000 | LLM orchestration, Auth, Sessions, Agent Registry | **Yes** |
| **Linux Agent** | 4001 | Isolated tool execution (terminal, files) | No |
| **Windows Agent** | 8081 | Desktop automation (mouse, keyboard, vision) | No |

### Docker Services

| Service | Image | Dockerfile | Description |
|---------|-------|------------|-------------|
| `core` | proxi-core | `backend/Dockerfile` | Full backend with DB, Auth, LLM |
| `agent` | proxi-agent | `backend/Dockerfile.agent` | Minimal, tools only |
| `frontend` | proxi-frontend | `frontend/Dockerfile` | React static build |

---

## 4. Key Patterns

### 4.1 The Verifiable Agent (Triple Handshake)

Proxi never blindly trusts LLM output. Every mission goes through:

1. **Assign:** `assign_mission(goal="Fix CPU spike", criteria={"cpu_threshold": 50})`
2. **Execute:** Agent calls tools, explains reasoning before each action
3. **Report:** Agent claims task complete with summary
4. **Verify:** Orchestrator runs independent system check (psutil, HTTP, screenshot)
5. **Judge:** If verification fails, agent retries or escalates to human

### 4.2 Transparency Protocol

The agent MUST explain before every tool call:
```
Agent: "I will check system health to assess CPU usage..."
Tool:  get_system_health() → {'cpu_percent': 99.8, 'status': 'critical'}
Agent: "CPU is critical at 99.8%. I will identify the culprit process..."
Tool:  run_terminal_command("top -bn1") → ffmpeg_transcode at 99.8%
Agent: "Found ffmpeg_transcode consuming CPU. I will terminate it..."
```

### 4.3 Agent Proxy Pattern

Core routes tool calls to the active agent via HTTP:

```
1. User selects agent in UI
   └─▶ POST /api/workstations/{id}/activate

2. User sends chat message
   └─▶ POST /api/chat
       └─▶ GeminiService.process_message()
           └─▶ LLM decides to call tool
               └─▶ AgentProxy.execute_tool()
                   └─▶ HTTP POST to agent /execute
                       └─▶ Agent executes tool
                           └─▶ Result returned to Core
```

---

## 5. /execute Contract

All agents must implement this endpoint:

**Request:**
```json
POST /execute
{
  "tool_name": "run_terminal_command",
  "parameters": {"command": "ls -la"}
}
```

**Response:**
```json
{
  "success": true,
  "result": "file1.txt\nfile2.txt",
  "error": null
}
```

### Supported Tools

| Tool | Linux | Windows | Description |
|------|-------|---------|-------------|
| `run_terminal_command` | ✓ | ✓ | Execute shell commands |
| `get_system_health` | ✓ | ✓ | CPU/memory/disk metrics |
| `open_target` | ✓ | ✓ | Open URLs/files |
| `wait_seconds` | ✓ | ✓ | Delay execution |
| `click_at` | ✗ | ✓ | Mouse click at coordinates |
| `type_text` | ✗ | ✓ | Keyboard input |
| `press_hotkey` | ✗ | ✓ | Key combinations |
| `get_screenshot_base64` | ✗ | ✓ | Screen capture |
| `scan_ui_tree` | ✗ | ✓ | Windows UI automation |
| `focus_window` | ✗ | ✓ | Window management |
| `list_windows` | ✗ | ✓ | List open windows |

---

## 6. Tech Stack

### AI Models
| Role | Model | Purpose |
|------|-------|---------|
| **Fast Reasoning** | `gemini-2.0-flash` | Quick responses, tool execution |
| **Deep Reasoning** | `gemini-2.5-pro-preview` | Complex multi-step tasks |
| **Vision Analysis** | `gemini-2.0-flash` | Screenshot analysis, UI verification |
| **Voice (Frontend)** | Gemini Live Native Audio | WebRTC voice I/O |

### Backend
- **Language:** Python 3.12+
- **Framework:** FastAPI + Uvicorn
- **SDK:** `google-generativeai` (Stable)
- **Streaming:** NDJSON (Newline Delimited JSON)
- **Database:** SQLite with WAL mode

### Desktop Automation
- **Mouse/Keyboard:** PyAutoGUI
- **Windows UI:** PyWinAuto
- **System Metrics:** psutil
- **Clipboard:** pyperclip

### Frontend
- **Framework:** React 18 + TypeScript
- **Styling:** Tailwind CSS
- **Build:** Vite
- **Voice:** Gemini Live WebRTC

---

## 7. Key Files

| Component | File | Description |
|-----------|------|-------------|
| Core Server | `backend/main.py` | FastAPI with all endpoints |
| Agent Server | `backend/agent_server.py` | Lightweight, tools only |
| Gemini Service | `backend/services/gemini_service.py` | AI orchestration (45 tools) |
| Agent Proxy | `backend/services/agent_proxy.py` | Routes calls to agents |
| Desktop Factory | `backend/services/desktop/factory.py` | OS-based service selection |
| Workstation Registry | `backend/registry/workstation_registry.py` | Multi-agent management |
| Command Guard | `backend/tools/command_guard.py` | Security guardrails |
| Frontend App | `frontend/App.tsx` | Main React app |
| Voice Hook | `frontend/hooks/useGeminiLive.ts` | WebRTC voice handling |

---

## 8. API Endpoints

### Core (Port 4000)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat` | POST | Send message, get streaming response |
| `/api/auth/login` | POST | Authenticate user |
| `/api/auth/logout` | POST | End session |
| `/api/sessions` | GET/POST | Session management |
| `/api/workstations` | GET | List registered agents |
| `/api/workstations/{id}/activate` | POST | Set active agent |

### Agent (Port 4001/8081)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Agent health + metrics |
| `/execute` | POST | Execute a tool |
| `/capabilities` | GET | List available tools |

---

*For deployment instructions, see [DEPLOYMENT.md](./DEPLOYMENT.md)*  
*For usage guide, see [USER_GUIDE.md](../USER_GUIDE.md)*
