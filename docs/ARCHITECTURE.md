# Proxi System Architecture

**Version:** v3.4.0  
**Last Updated:** January 31, 2026  
**Last Commit:** `c36b12d` - PWA support, zero-downtime deploy, advanced PPT tools  
**Status:** ⚠️ Testing Pending

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
| `forensic-investigation` | proxi-forensics | External build | SOC training container |

### Port Configuration

Core communicates with agents via Docker internal networking or Tailscale. **Always use internal port 8081** in workstation config:

| Agent | External Port | Internal Port | workstations.json |
|-------|--------------|---------------|-------------------|
| Linux Agent (Docker) | 4001 | 8081 | `"host": "agent", "port": 8081` |
| Forensics (Docker) | 5081 | 8081 | `"host": "forensic-investigation", "port": 8081` |
| Windows Agent (Tailscale) | - | 8081 | `"host": "100.x.x.x", "port": 8081` |

**Why?** Core runs inside Docker and connects via internal network (service names) or Tailscale (direct IP). External ports (4001, 5081) are only for debugging from host.

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
| `get_observation` | ✗ | ✓ | **NEW** Combined screenshot + UI tree + SoM overlay |
| `scan_ui_tree` | ✗ | ✓ | Windows UI automation |
| `focus_window` | ✗ | ✓ | Window management |
| `list_windows` | ✗ | ✓ | List open windows |
| `open_app` | ✗ | ✓ | **NEW** Launch application by name |
| `draw_shape` | ✗ | ✓ | **NEW** Draw shapes in PowerPoint |
| `ppt_add_chart` | ✗ | ✓ | **NEW** Insert charts with data |
| `ppt_add_table` | ✗ | ✓ | **NEW** Insert formatted tables |
| `ppt_add_icon` | ✗ | ✓ | **NEW** Insert icons from library |
| `ppt_insert_smartart` | ✗ | ✓ | **NEW** Insert SmartArt diagrams |

---

## 6. Execution Modes (v3.1.0) (section updated on 30-01-2026)

Proxi supports three execution modes selectable via the frontend Settings panel:

| Mode | Model | Max Turns | Verification | Use Case |
|------|-------|-----------|--------------|----------|
| **Quick** ⚡ | Flash | 5 | Skip | Simple queries, status checks |
| **Balanced** ⚖️ | Flash | 10 | Auto (action tasks) | Default - most tasks |
| **Thorough** 🔬 | Pro | 15 | Always | Critical ops, complex multi-step |

### Mode Configuration (backend)
```python
MODE_CONFIGS = {
    "quick":    {"model": "flash", "verify": False,  "max_turns": 5},
    "balanced": {"model": "flash", "verify": "auto", "max_turns": 10},
    "thorough": {"model": "pro",   "verify": True,   "max_turns": 15}
}
```

### Stall Recovery (v3.1.0)
If the Gemini API stops responding mid-conversation:
1. Backend detects empty response and emits `stalled` event
2. Frontend shows "Continue" button
3. User can click to send "Please continue where you left off"
4. Session history preserved for seamless resumption

---

## 7. Tech Stack

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

## 8. Key Files

| Component | File | Description |
|-----------|------|-------------|
| Core Server | `backend/main.py` | FastAPI with all endpoints |
| Agent Server | `backend/agent_server.py` | Lightweight, tools only |
| Gemini Service | `backend/services/gemini_service.py` | AI orchestration (70+ tools) |
| Agent Proxy | `backend/services/agent_proxy.py` | Routes calls to agents |
| Desktop Factory | `backend/services/desktop/factory.py` | OS-based service selection |
| Workstation Registry | `backend/registry/workstation_registry.py` | Multi-agent management |
| Command Guard | `backend/tools/command_guard.py` | Security guardrails |
| Frontend App | `frontend/App.tsx` | Main React app |
| Voice Hook | `frontend/hooks/useGeminiLive.ts` | WebRTC voice handling |

---

## 9. API Endpoints

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
| `/ground` | POST | **NEW** Visual grounding with local Gemini (requires `GEMINI_API_KEY` on agent) |

---

## 10. Future Plans

### Supervisory Multi-Agent Architecture (Planned)
A hierarchical agent system where a Supervisor LLM orchestrates multiple specialized agents:

```
┌─────────────────────────────────────────────┐
│           SUPERVISOR (Pro Model)            │
│  - Decomposes complex tasks into subtasks   │
│  - Assigns to appropriate specialist agents │
│  - Monitors progress and handles failures   │
│  - Synthesizes final results                │
└─────────────────┬───────────────────────────┘
                  │
    ┌─────────────┼─────────────┐
    ▼             ▼             ▼
┌────────┐  ┌────────┐  ┌────────┐
│Research│  │Execute │  │Verify  │
│ Agent  │  │ Agent  │  │ Agent  │
│(Flash) │  │(Flash) │  │(Flash) │
└────────┘  └────────┘  └────────┘
```

**Benefits:**
- Better task planning for complex investigations
- Parallel execution of independent subtasks
- Specialized agents for different domains (security, automation, analysis)
- Cost optimization (supervisor uses Pro only for planning)

**Status:** Not implemented. Current system uses single-agent with mode-based constraints.

### Admin Panel Mode Configuration (Planned)
- Web UI to edit `backend/config/modes.json`
- Real-time mode adjustment without restart
- Custom mode creation for specific use cases

---

*For deployment instructions, see [DEPLOYMENT.md](./DEPLOYMENT.md)*  
*For usage guide, see [USER_GUIDE.md](../USER_GUIDE.md)*


## fututre plan - multi-agent workflow

Multi-Agent Routing Analysis
Current Architecture (Single Active Agent)
Frontend                    Backend (Core)                    Agents
─────────                   ──────────────                    ──────
[Agent Selector] ──POST──▶ /api/workstations/{id}/activate
                           │
                           ▼
                    set_active_agent(url)  ← GLOBAL VARIABLE
                    (_active_agent_url)
                           │
[Send Message] ───POST───▶ /api/chat
                           │
                           ▼
                    gemini_service.py
                           │
                    get_desktop_service()
                           │
                           ▼
                    ProxyDesktopService(_active_agent_url)
                           │
                           ▼
                    HTTP /execute ─────────────────────▶ [Single Agent]
Key Files:

File	Role
@e:\data\proxi-ai\backend\services\desktop\factory.py:8	_active_agent_url global
@e:\data\proxi-ai\backend\main.py:932	set_active_agent(agent_url)
@e:\data\proxi-ai\backend\services\gemini_service.py:217-224	Gets OS type from active agent
Changes Needed for Multi-Agent
Approach A: LLM-Driven Agent Selection (Recommended)
Let Gemini decide which agent to use based on the task.

Layer	Change	Effort
Frontend	Multi-select agents (checkboxes instead of radio)	2 hrs
Backend API	New endpoint: POST /api/chat accepts available_agents: string[]	1 hr
Gemini Service	Add select_agent tool for LLM to pick agent	3 hrs
Factory	Pass agent_url per-tool-call instead of global	2 hrs
System Prompt	Teach LLM about available agents + when to switch	1 hr
Total Effort: ~9 hours (1-2 days)

Implementation Sketch
python
### New tool for LLM
def select_agent(agent_id: str) -> dict:
    """Switch to a different agent for subsequent tool calls."""
    if agent_id not in available_agents:
        return {"error": f"Agent {agent_id} not available"}
    set_active_agent(agent_id)
    return {"success": True, "active_agent": agent_id}
python
### System prompt addition
"""
You have access to multiple agents:
- linux-container: Terminal, git, python (Linux)
- win-desktop: Desktop automation, Office, CRM (Windows)
 
When a task requires capabilities from a different agent:
1. Use select_agent(agent_id) to switch
2. Then use the required tools
"""
Approach B: Parallel Multi-Agent (Complex)
Execute tools on multiple agents simultaneously.

Change	Effort
Modify execute_tool to accept agent_id param	2 hrs
Update all 48+ tool definitions	4 hrs
Batch/parallel execution coordinator	4 hrs
Result aggregation logic	3 hrs
Frontend multi-result display	3 hrs