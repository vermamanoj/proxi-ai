# 03 — Backend Services

## Overview

The backend is organized into distinct service layers, each with a single responsibility:

| Service | File | Lines | Responsibility |
|---------|------|-------|---------------|
| FastAPI App | `backend/main.py` | 980 | HTTP endpoints, auth middleware, SSE streaming, session CRUD |
| Gemini Orchestrator | `backend/services/gemini_service.py` | 1933 | LLM interaction, tool registration, multi-turn loop, approval flow |
| Mission Orchestrator | `backend/services/orchestrator.py` | 197 | Triple Handshake verification lifecycle |
| Agent Proxy | `backend/services/agent_proxy.py` | 166 | HTTP proxy for Core → Agent tool calls |
| Auth Service | `backend/auth/auth_service.py` | 581 | User management, sessions, magic links |
| Workstation Registry | `backend/registry/workstation_registry.py` | 301 | Agent registration, health checks |
| Database | `backend/database.py` | 322 | SQLite persistence for missions, sessions, images |
| Logger | `backend/utils/logger.py` | 30 | Centralized logging to stdout + file |

---

## 1. FastAPI Core (`main.py`)

### Initialization

On startup, `main.py`:
1. Loads `.env` via `python-dotenv`
2. Creates FastAPI app with CORS middleware (configurable origins)
3. Initializes singleton services: `AuthService`, `GeminiService`, `Database`, `WorkstationRegistry`
4. Registers startup/shutdown events for DB connection management

### Endpoint Groups

#### Authentication (`/api/auth/`)

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/api/auth/login` | POST | None | Username/password login → set session cookie |
| `/api/auth/logout` | POST | Session | Invalidate session |
| `/api/auth/me` | GET | Session | Get current user info |
| `/api/auth/magic-link/{token}` | GET | None | Redeem magic link → set session cookie |
| `/api/admin/magic-links` | POST | Admin | Create new magic link |
| `/api/admin/magic-links` | GET | Admin | List all magic links |
| `/api/admin/login-events` | GET | Admin | View login history |

#### Chat (`/api/chat`)

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/api/chat` | POST (SSE) | Session | Main chat endpoint — streams LLM response |
| `/api/chat/cancel` | POST | Session | Cancel in-progress chat |
| `/api/approve/{approval_id}` | POST | Session | Approve pending command |

The chat endpoint returns a `StreamingResponse` with `text/event-stream` content type. Each line is a JSON object with a `type` field.

#### Sessions (`/api/sessions/`)

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/api/sessions` | GET | Session | List user's sessions |
| `/api/sessions/{id}` | GET | Session | Get session with messages |
| `/api/sessions/{id}` | DELETE | Session | Delete a session |
| `/api/sessions/{id}/title` | PUT | Session | Rename session |

#### Workstations (`/api/workstations/`)

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/api/workstations` | GET | Session | List registered agents |
| `/api/workstations` | POST | Session | Register new agent |
| `/api/workstations/{id}` | DELETE | Admin | Remove agent |
| `/api/workstations/{id}/health` | GET | Session | Health check agent |
| `/api/workstations/health-all` | GET | Session | Health check all agents |
| `/api/workstations/{id}/select` | POST | Session | Set active agent for session |

#### File Proxy (`/api/files/`)

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/api/files/download` | POST | Session | Download file from agent → user |
| `/api/files/upload` | POST | Session | Upload file from user → agent |

### Auth Middleware

```python
async def require_auth(request: Request) -> dict:
    session_id = request.cookies.get("session_id")
    user = validate_session(session_id)
    if not user:
        raise HTTPException(401, "Not authenticated")
    return user
```

All protected endpoints use `Depends(require_auth)`. Admin endpoints additionally check `user["role"] == "admin"`.

### SSE Streaming Pattern

```python
@app.post("/api/chat")
async def chat(request: ChatRequest, user = Depends(require_auth)):
    async def event_stream():
        async for event in gemini_service.route_and_execute_stream(...):
            yield json.dumps(event) + "\n"
            # Periodic session save every 5 tool calls
            if event.get("type") == "tool_result" and tool_count % 5 == 0:
                database.save_session(session)
    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

---

## 2. Gemini Orchestrator (`gemini_service.py`)

This is the largest and most complex file (1933 lines). It manages the entire LLM interaction lifecycle.

### Class: `GeminiService`

#### Initialization

```python
class GeminiService:
    def __init__(self):
        genai.configure(api_key=GEMINI_API_KEY)
        self.sessions = {}           # session_id → chat history
        self.pending_approvals = {}  # approval_id → command details
        self.evidence_store = {}     # evidence_id → evidence data
        self.tools_map = {}          # tool_name → callable
        self._register_tools()
```

#### Tool Registration

`_register_tools()` populates `self.tools_map` with 48+ tool functions and builds `genai.Tool` declarations with parameter schemas for the Gemini API.

Tools are categorized:
- **System tools**: `get_system_health`, `get_server_time`, `run_terminal_command`
- **Desktop tools**: `click_at`, `type_text`, `press_hotkey`, `scroll_page`, `focus_window`, etc.
- **Vision tools**: `look_at_screen`, `share_screenshot`, `ground_and_click`
- **Macro tools**: `open_app`, `navigate_app`, `interact_element`, `fill_form`, `draw_shape`, `perform_workflow`
- **PPT tools**: 20+ PowerPoint operations
- **Mission tools**: `assign_mission`, `report_execution`, `escalate_to_human`
- **Evidence tools**: `store_evidence`, `get_evidence`, `list_evidence`, `render_attack_path`
- **Integration tools**: `send_slack_message`, `create_linear_ticket`, `update_github_file`, `create_github_issue`
- **File tools**: `save_uploaded_image`, `send_file_to_user`

#### System Prompt Assembly

```python
def _build_system_prompt(self, mode_config, agent_os, agent_id):
    prompt_sections = mode_config.get("prompt_sections", ["base"])
    prompt = ""
    for section in prompt_sections:
        path = f"backend/config/prompts/{section}.md"
        # or "backend/config/prompts/workflows/{section}.md"
        template = read_file(path)
        prompt += template.format(
            agent_os=agent_os,
            shell_type="PowerShell" if "windows" else "Bash",
            mode=mode_name,
            max_tool_calls=mode_config["max_tool_calls"],
            timeout=mode_config["timeout"],
            ...
        )
    return prompt
```

#### Main Orchestration Loop: `route_and_execute_stream()`

This is the core async generator (500+ lines). Key stages:

1. **Session setup** — Load/create session, trim history to `session_history_size`
2. **Direct command detection** — `!command` prefix → bypass LLM, run through guardrails
3. **Model selection** — `modes.json` configures `gemini-2.0-flash` or `gemini-2.0-pro`
4. **Voice mode detection** — Prefixes like "explain:", "investigate:", "prove:", "summarize:" inject behavior modifiers
5. **Image handling** — Base64 images embedded in request are included as multimodal content
6. **Agent context injection** — `[CURRENT AGENT: {os} - use {shell}]` prepended to every message
7. **Multi-turn loop**:
   - Send content to Gemini → receive response parts
   - Parse text (stream as `llm_thought`) and function calls
   - Extract MISSION/PLAN/GOAL_UPDATE markers from text
   - Execute function calls sequentially via `tools_map`
   - Handle special return values: `APPROVAL_REQUIRED:`, `BLOCKED:`, `ESCALATED`, `__SCREENSHOT__`, `__FILE__`
   - Feed tool results back to model
   - Respect `max_tool_calls` limit
8. **Error recovery** — On exception, save partial content for "continue" resumption
9. **Session persistence** — Save updated history to DB

#### Key Tool Wrappers

**`run_terminal_command`** — The most important tool wrapper:
```python
def run_terminal_command(self, command, session_id=None):
    check_result = check_command_safety(command)
    if check_result.risk_level == CommandRisk.BLOCKED:
        return f"BLOCKED: {check_result.reason}"
    if check_result.risk_level == CommandRisk.NEEDS_APPROVAL:
        # Check if already approved this session
        if command_hash in self.approved_commands.get(session_id, set()):
            pass  # Auto-approve
        else:
            approval_id = secrets.token_urlsafe(16)
            self.pending_approvals[approval_id] = {...}
            return f"APPROVAL_REQUIRED:{approval_id}:{check_result.reason}"
    return get_desktop_service().run_terminal_command(command)
```

**`look_at_screen`** — Enhanced observation:
```python
def look_at_screen(self, task_context=""):
    obs = get_desktop_service().get_observation(include_som=True)
    # Sends screenshot + UI element list to Gemini Vision
    # Returns structured analysis with element descriptions
```

**`ground_and_click`** — Visual grounding:
```python
def ground_and_click(self, element_description):
    # Try agent-local grounding first (fast, no round-trip)
    # Fall back to Core-side Gemini Vision
    # Click at identified coordinates
```

---

## 3. Mission Orchestrator (`orchestrator.py`)

Implements the Triple Handshake pattern for verifiable task execution.

### Mission Lifecycle

```
assign_mission(goal, criteria)     ──► Status: ASSIGNED
      │
      ▼
[Agent executes tools]
      │
      ▼
report_execution(id, summary)      ──► Status: PENDING_VERIFICATION
      │
      ▼
verify_mission(id)                 ──► Status: VERIFIED / FAILED
      │
      ├─► finalize_mission(id, "verified")   ──► Status: VERIFIED
      └─► escalate_to_human(id, reason)      ──► Status: ESCALATED
```

### Verification Types

| Type | Criteria JSON | Verification Method |
|------|--------------|---------------------|
| `process_killed` | `{"type": "process_killed", "pid": 1234}` | `psutil.pid_exists()` |
| `process_exists` | `{"type": "process_exists", "name": "nginx"}` | Process name check |
| `file_exists` | `{"type": "file_exists", "path": "/tmp/backup.tar"}` | `os.path.exists()` |
| `service_stopped` | `{"type": "service_stopped", "name": "apache2"}` | Platform-specific |
| `cpu` | `{"type": "cpu", "threshold": 80}` | System health check |
| `http` | `{"type": "http", "url": "...", "expected_status": 200}` | HTTP request |
| `visual` | `{"type": "visual", "description": "..."}` | Screenshot + LLM analysis |

### QA Verification

After tool-based verification, an independent Gemini model call acts as QA auditor:

```python
def _verify_outcome(self, claim, evidence, criteria):
    prompt = f"As a QA auditor, verify: Claim={claim}, Evidence={evidence}, Criteria={criteria}"
    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content(prompt)
    # Parse VERIFIED/FAILED from response
```

---

## 4. Agent Proxy (`agent_proxy.py`)

Lightweight HTTP client for Core → Agent communication.

### Class: `AgentProxy`

```python
class AgentProxy:
    def __init__(self):
        self.timeout = aiohttp.ClientTimeout(total=30)
        self._active_agent_id = None

    async def execute_tool(self, tool_name, parameters, agent_id=None):
        url = f"{agent_url}/execute"
        headers = {"X-Agent-Key": AGENT_API_KEY}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                return await resp.json()

    def execute_tool_sync(self, tool_name, parameters, agent_id=None):
        # ThreadPoolExecutor bridge for sync callers
```

The proxy resolves agent URLs from the WorkstationRegistry and includes `X-Agent-Key` for authentication.

---

## 5. Logger (`utils/logger.py`)

Simple centralized logger:

```python
def log_system(message, category="INFO"):
    formatted = f"[{timestamp}] [{category}] {message}"
    print(formatted, flush=True)        # stdout (uvicorn captures)
    open(DEBUG_LOG_PATH, "a").write(...)  # file persistence
```

Log file: `proxi_debug.log` (at repo root or `/app/data/` in Docker).

---

## Singleton Pattern

All major services use module-level singleton instances with lazy initialization:

```python
_auth_service: AuthService = None

def get_auth_service() -> AuthService:
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service
```

This pattern is used for: `AuthService`, `GeminiService`, `Database`, `WorkstationRegistry`, `AgentProxy`, `DesktopService`.

---

*Previous: [Architecture ←](02_architecture.md) | Next: [Agent System →](04_agent_system.md)*
