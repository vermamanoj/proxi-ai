# 02 — System Architecture

## Three-Tier Split Architecture

Proxi uses a strict security-first separation between UI, intelligence, and execution:

```
┌─────────────────┐          ┌─────────────────┐          ┌─────────────────────┐
│    FRONTEND      │  HTTP/   │   PROXI CORE     │  HTTP/   │   PROXI AGENT(s)    │
│  React + Vite    │  SSE     │   FastAPI         │  JSON    │   FastAPI            │
│                  │ ───────► │                   │ ───────► │                     │
│  - Chat UI       │  :4002   │  - LLM Orchestr.  │  :4000   │  - Desktop Control  │
│  - Voice I/O     │          │  - Auth + Sessions │          │  - Terminal Exec    │
│  - Approval Flow │          │  - Command Guard   │          │  - Screenshots      │
│  - Mission View  │          │  - Mission Mgmt    │          │  - PPT Automation   │
│                  │          │  - GEMINI_API_KEY  │          │  - Visual Grounding │
└─────────────────┘          └─────────────────┘          └─────────────────────┘
       UI Only                    Brain                          Hands
    (No secrets)             (Holds all keys)              (No DB, no user keys)
```

> **Performance note:** While the design principle is "agents hold no keys," Windows agents are deliberately given `GEMINI_API_KEY` for **local visual grounding** via the `/ground` endpoint. Without this, every screen interpretation requires a round-trip to Core (screenshot upload → Core calls Gemini Vision → returns coordinates), adding significant latency to GUI automation. With the key on the agent, grounding happens locally in ~200ms instead of ~2s.

### Why Split?

| Concern | Solution |
|---------|----------|
| **API Key Security** | Core holds `GEMINI_API_KEY` + user DB; Windows agents hold `GEMINI_API_KEY` only for local visual grounding (deliberate performance trade-off) |
| **Blast Radius** | Compromised agent can't access user DB, sessions, or LLM API |
| **Multi-Agent** | Core can route to N agents (Linux containers, Windows VMs, remote machines) |
| **Scalability** | Agents are stateless; Core manages all state |

---

## Component Relationships

```
                    ┌──────────────────────────────────────────┐
                    │              PROXI CORE                   │
                    │                                          │
                    │  main.py ──► GeminiService                │
                    │     │            │                        │
                    │     │            ├─► tools_map{}          │
                    │     │            │     └─► run_terminal.. │
                    │     │            │     └─► look_at_screen │
                    │     │            │     └─► ppt_edit_text  │
                    │     │            │     └─► ... (48+)      │
                    │     │            │                        │
                    │     │            ├─► CommandGuard          │
                    │     │            │     └─► check_safety() │
                    │     │            │                        │
                    │     │            └─► get_desktop_service() │
                    │     │                      │              │
                    │     ├─► AuthService         │              │
                    │     ├─► Database             │              │
                    │     ├─► WorkstationRegistry  │              │
                    │     └─► Orchestrator         │              │
                    │                              │              │
                    └──────────────────────────────┼──────────────┘
                                                   │
                                    DesktopService Factory
                                         │
                        ┌────────────────┼────────────────┐
                        │                │                │
                   ProxyDesktop     RealDesktop       NullDesktop
                   (Remote Agent)  (Local Windows)   (No Agent)
                        │
                   HTTP POST /execute
                        │
                        ▼
               ┌─────────────────┐
               │  PROXI AGENT    │
               │                 │
               │  agent_server   │
               │    └─► local    │
               │       desktop   │
               │       service   │
               └─────────────────┘
```

---

## Data Flow: Chat Request

### 1. User Sends Message

```
[Phone/Browser] → POST /api/chat (SSE stream)
    Headers: Cookie: session_id=abc123
    Body: { message: "Kill the high-CPU process", mode: "balanced", session_id: "..." }
```

### 2. Core Processing Pipeline

```
main.py: /api/chat
  │
  ├─ 1. Auth Check ──► require_auth() validates session cookie
  │
  ├─ 2. Session Load ──► Database.get_session() or create new
  │
  ├─ 3. Direct Command? ──► "!command" prefix bypasses LLM
  │     └─► CommandGuard.check_safety() → execute or block
  │
  ├─ 4. Mode Config ──► modes.json selects model, limits, prompt sections
  │
  ├─ 5. Prompt Assembly ──► Concatenate prompt .md modules per mode
  │     └─► Inject: {agent_os}, {shell_type}, {mode}, {max_tool_calls}
  │
  ├─ 6. GeminiService.route_and_execute_stream()
  │     │
  │     ├─ Create GenerativeModel with tools + system instruction
  │     │
  │     ├─ LOOP (max_turns):
  │     │   ├─ Send to Gemini → Parse response (text + function_calls)
  │     │   ├─ Stream SSE events: llm_thought, plan, goal_update, final_response
  │     │   ├─ Execute tool calls sequentially:
  │     │   │   ├─ tools_map[name](params)
  │     │   │   │   └─► get_desktop_service() → ProxyDesktopService
  │     │   │   │       └─► HTTP POST agent:8081/execute
  │     │   │   ├─ Handle: APPROVAL_REQUIRED, BLOCKED, ESCALATED
  │     │   │   └─ Handle: __SCREENSHOT__, __FILE__ markers
  │     │   ├─ Send tool results back to model
  │     │   └─ Check tool_call_count < max_tool_calls
  │     │
  │     └─ Final response + session save
  │
  └─ 7. SSE Stream ──► JSON-line events to frontend
```

### 3. SSE Event Types

| Event | Purpose |
|-------|---------|
| `llm_thought` | Real-time streaming of LLM reasoning |
| `final_response` | Complete response text chunk |
| `screenshot` | Base64 screenshot image |
| `file` | Base64 file for download |
| `approval_request` | Command needs user approval |
| `mission` | Mission status update |
| `plan` | PLAN_START/PLAN_END structured plan |
| `goal_update` | G1 ACTIVE / G1 COMPLETE progress |
| `error` | Error message |
| `done` | Stream complete |

---

## Data Flow: Tool Execution

```
GeminiService                     DesktopService Factory              Agent
    │                                    │                              │
    │  run_terminal_command("ls")         │                              │
    ├──────────────────────────────────►  │                              │
    │                                    │                              │
    │  1. CommandGuard.check_safety()     │                              │
    │     → SAFE / NEEDS_APPROVAL / BLOCKED                             │
    │                                    │                              │
    │  2. get_desktop_service()           │                              │
    │     → ProxyDesktopService           │                              │
    │                                    │                              │
    │  3. proxy._execute_sync()           │                              │
    │     ├─ Build URL: agent:8081/execute │                              │
    │     ├─ Add X-Agent-Key header       │                              │
    │     └─ HTTP POST ──────────────────────────────────────────────►  │
    │                                    │                              │
    │                                    │     4. agent_server dispatch  │
    │                                    │        tool_name → method     │
    │                                    │        ds.run_terminal_cmd()  │
    │                                    │                              │
    │     5. Return result ◄─────────────────────────────────────────── │
    │        {success: true, result: "..."} │                              │
    │                                    │                              │
```

---

## Deployment Topology

### Docker Compose (Development / Demo)

```
┌─────────────────────────────────────────────────┐
│                 Host Machine (Windows)            │
│                                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│  │ Frontend  │  │  Core    │  │ Linux Agent   │   │
│  │ :4002     │  │ :4000    │  │ :4001→:8081   │   │
│  │ (Vite)    │  │ (uvicorn)│  │ (uvicorn)     │   │
│  └──────────┘  └──────────┘  └──────────────┘   │
│                      │                            │
│                      │  host.docker.internal      │
│                      ▼                            │
│              ┌──────────────┐                     │
│              │ Windows Agent │ (native, :8081)     │
│              │ (separate     │                     │
│              │  repo clone)  │                     │
│              └──────────────┘                     │
└─────────────────────────────────────────────────┘
```

### Production (Multi-Machine)

```
┌────────────────────┐     Tailscale      ┌────────────────────┐
│  Oracle Cloud VM   │ ◄──────────────── │  Windows Server     │
│  (Ubuntu)          │     100.x.y.z      │                    │
│                    │                    │  Windows Agent      │
│  Frontend :4002    │                    │  :8081              │
│  Core     :4000    │                    │                    │
│  Linux Agent :4001 │                    │  PowerPoint, CRM,  │
│                    │                    │  Desktop apps       │
└────────────────────┘                    └────────────────────┘
```

### Port Mapping

| Service | Container Port | Host Port | Protocol |
|---------|---------------|-----------|----------|
| Frontend | 5173 | 4002 | HTTP |
| Core | 8000 | 4000 | HTTP/SSE |
| Linux Agent | 8081 | 4001 | HTTP |
| Windows Agent | 8081 | 8081 (native) | HTTP |

---

## Service Communication

### Core ↔ Agent Protocol

All agent communication uses HTTP with `X-Agent-Key` authentication:

| Endpoint | Method | Direction | Purpose |
|----------|--------|-----------|---------|
| `/health` | GET | Core → Agent | Health check + system metrics |
| `/execute` | POST | Core → Agent | Execute a tool by name |
| `/ground` | POST | Core → Agent | Visual grounding (local Gemini) |
| `/capabilities` | GET | Core → Agent | List available tools |
| `/files/download` | POST | Core → Agent | Download file as base64 |
| `/files/upload` | POST | Core → Agent | Upload file as base64 |

### Frontend ↔ Core Protocol

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/chat` | POST (SSE) | Chat with streaming response |
| `/api/auth/login` | POST | Authenticate user |
| `/api/auth/magic-link/:token` | GET | Passwordless login |
| `/api/sessions` | GET | List user sessions |
| `/api/workstations` | GET/POST | Manage agent registry |
| `/api/workstations/:id/health` | GET | Check agent health |
| `/api/approve/:id` | POST | Approve pending command |

---

## Key Design Decisions

### 1. Security Isolation
Core never executes desktop tools locally. Even when running on the same machine, tools are proxied to an agent process. This ensures a compromised agent can't access user DB, sessions, or API keys.

### 2. Stateless Agents
Agents hold no session state, no user data, no conversation history. They receive a tool call, execute it, and return the result. All state lives in Core.

### 3. Factory Pattern for Desktop Services
`get_desktop_service()` returns the appropriate implementation based on context:
- **ProxyDesktopService** — when an active remote agent is selected (normal operation)
- **RealDesktopService** — when `allow_local=True` (agent server running locally on Windows)
- **LinuxDesktopService** — when running on Linux (agent container)
- **NullDesktopService** — when no agent is selected (blocks all operations)
- **MockDesktopService** — when `RUNTIME_MODE=DEMO` (simulated responses)

### 4. Streaming Architecture
Chat responses use Server-Sent Events (SSE) for real-time streaming. The `route_and_execute_stream()` method is an async generator that yields JSON-line events as the LLM reasons, calls tools, and produces results.

### 5. Sync-in-Async Bridge
Gemini SDK tool functions must be synchronous, but agent communication is async HTTP. The `ProxyDesktopService` uses `ThreadPoolExecutor` + `asyncio.run()` to bridge this gap.

---

*Previous: [Overview ←](01_overview.md) | Next: [Backend Services →](03_backend_services.md)*
