# 10 — Developer Guide

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.12+ | Backend runtime |
| Node.js | 18+ | Frontend build |
| Docker Desktop | Latest | Container orchestration |
| Git | Latest | Version control |
| PowerShell | 7+ | Windows scripting |

Optional:
- **Tailscale** — For remote Windows agent connectivity
- **PowerPoint** — For PPT automation testing (Windows only)

---

## Local Development Setup

### 1. Clone & Environment

```powershell
git clone <repo-url> E:\data\proxi-ai
cd E:\data\proxi-ai

# Create .env from template
Copy-Item .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

### 2. Backend (Core) Setup

```powershell
cd E:\data\proxi-ai

# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies (Windows full stack)
pip install -r backend\requirements.txt

# Run Core server
python -m uvicorn backend.main:app --host 0.0.0.0 --port 4000 --reload
```

### 3. Frontend Setup

```powershell
cd E:\data\proxi-ai\frontend

npm install
npm run dev
# → http://localhost:5173 (or 4002 via Docker)
```

### 4. Agent Setup (Optional — for local testing)

```powershell
# In a separate terminal
.\venv\Scripts\Activate.ps1
python -m uvicorn backend.agent_server:app --host 0.0.0.0 --port 8081 --reload
```

### 5. Docker Compose (Alternative)

```powershell
docker compose build
docker compose up -d
# Frontend: http://localhost:4002
# Core: http://localhost:4000
# Agent: http://localhost:4001
```

---

## Project Layout Quick Reference

```
backend/
├── main.py                      # FastAPI Core — start here for endpoints
├── agent_server.py              # FastAPI Agent — start here for agent logic
├── database.py                  # SQLite persistence
├── auth/
│   └── auth_service.py          # User auth, sessions, magic links
├── config/
│   ├── modes.json               # Execution mode definitions
│   └── prompts/                 # System prompt modules (.md)
│       ├── base.md
│       ├── verifiable_agent.md
│       ├── mission_planning.md
│       ├── command_guard.md
│       ├── tools_quick_ref.md
│       └── workflows/
│           ├── forensics.md
│           └── powerpoint.md
├── models/
│   └── api_models.py            # Pydantic request/response models
├── registry/
│   └── workstation_registry.py  # Agent registration + health checks
├── services/
│   ├── gemini_service.py        # Core AI orchestrator (largest file)
│   ├── orchestrator.py          # Triple Handshake missions
│   ├── agent_proxy.py           # Core→Agent HTTP proxy
│   └── desktop/                 # Desktop service implementations
│       ├── interface.py         # Abstract base class
│       ├── factory.py           # Service selection factory
│       ├── real.py              # Windows automation (PyAutoGUI+PyWinAuto)
│       ├── linux.py             # Linux terminal-only
│       ├── proxy_adapter.py     # HTTP proxy to remote agent
│       ├── null.py              # Blocks all ops (no agent selected)
│       └── mock.py              # Demo mode simulation
├── tools/
│   ├── command_guard.py         # Security guardrails
│   ├── ppt_tools.py             # PowerPoint COM automation
│   └── standard_tools.py        # Productivity + system tools
└── utils/
    └── logger.py                # Centralized logging
```

---

## Common Development Tasks

### Adding a New Tool

1. **Define the function** in the appropriate tools file (or `gemini_service.py` for tools that need orchestrator context):

```python
# In backend/tools/standard_tools.py (or new file)
def my_new_tool(param1: str, param2: int = 10) -> str:
    """Do something useful."""
    return f"Result: {param1} x {param2}"
```

2. **Register in GeminiService** (`gemini_service.py` → `_register_tools()`):

```python
# Add to tools_map
self.tools_map["my_new_tool"] = lambda p1, p2=10: my_new_tool(p1, p2)

# Add Gemini function declaration
tools.append(genai.protos.Tool(
    function_declarations=[
        genai.protos.FunctionDeclaration(
            name="my_new_tool",
            description="Do something useful",
            parameters=genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                properties={
                    "param1": genai.protos.Schema(type=genai.protos.Type.STRING, description="First param"),
                    "param2": genai.protos.Schema(type=genai.protos.Type.INTEGER, description="Second param"),
                },
                required=["param1"]
            )
        )
    ]
))
```

3. **If the tool runs on agents**, add dispatch in `agent_server.py`:

```python
elif tool_name == "my_new_tool":
    result = ds.my_new_tool(params.get("param1", ""), int(params.get("param2", 10)))
```

4. **If the tool is a desktop operation**, add the method to:
   - `desktop/interface.py` (abstract method)
   - `desktop/real.py` (Windows implementation)
   - `desktop/linux.py` (Linux stub or implementation)
   - `desktop/proxy_adapter.py` (proxy delegation)
   - `desktop/null.py` (error response)
   - `desktop/mock.py` (simulated response)

### Adding a New Prompt Module

1. Create `backend/config/prompts/my_module.md` (or `prompts/workflows/my_module.md`)
2. Use `{template_variables}` for dynamic content
3. Add module name to appropriate modes in `backend/config/modes.json`:

```json
"thorough": {
  "prompt_sections": ["base", "verifiable_agent", ..., "workflows/my_module"]
}
```

### Adding a New Execution Mode

Edit `backend/config/modes.json`:

```json
"expert": {
  "model": "gemini-2.0-pro-exp-02-05",
  "max_turns": 20,
  "max_tool_calls": 60,
  "timeout": 180,
  "verify": true,
  "prompt_sections": ["base", "verifiable_agent", "mission_planning", "command_guard", "tools_quick_ref", "workflows/forensics", "workflows/powerpoint"]
}
```

Then add the mode option to the frontend's mode selector component.

### Adding a New Desktop Service Implementation

1. Create `backend/services/desktop/my_service.py`
2. Inherit from `DesktopInterface`
3. Implement all abstract methods
4. Update `factory.py` to return your service under appropriate conditions

---

## Coding Conventions

### Python Style
- **Formatting**: Standard PEP 8
- **Type hints**: Used for function signatures, especially in interfaces
- **Docstrings**: Triple-quote docstrings for classes and public methods
- **Logging**: Use `log_system(message, category)` from `backend/utils/logger.py`
- **Error handling**: Return error strings from tool functions (not exceptions) — the LLM processes error messages as tool results

### Architecture Rules
- **Core never executes desktop tools locally** — always through proxy or agent
- **Agents are stateless** — no session data, no conversation history
- **Singletons** — Major services use module-level singleton pattern with `get_xxx()` functions
- **Tool functions must be synchronous** — Gemini SDK requires sync callables; use ThreadPoolExecutor for async bridges

### Security Rules
- **Never hardcode API keys** — use environment variables
- **Never bypass CommandGuard** — all terminal commands must go through `check_command_safety()`
- **Never store secrets in agent** — agents should not have access to user data

---

## Debugging

### Log Locations

| Log | Location | Content |
|-----|----------|---------|
| Core stdout | Terminal / `docker compose logs core` | All `print()` and `log_system()` output |
| Debug log file | `proxi_debug.log` (repo root or `/app/data/`) | Persistent copy of `log_system()` calls |
| Agent stdout | Terminal / `docker compose logs agent` | `[AGENT_EXEC]` entries with timing |
| Auth logs | `backend/auth/login_events.json` | Login attempts with IP and user-agent |

### Common Debug Patterns

**Tool not executing?**
```python
# Check if tool is registered
print(list(gemini_service.tools_map.keys()))

# Check if agent is reachable
curl -H "X-Agent-Key: $KEY" http://agent:8081/health
```

**Command blocked unexpectedly?**
```python
from backend.tools.command_guard import check_command_safety
result = check_command_safety("your command here")
print(f"Risk: {result.risk_level}, Reason: {result.reason}")
```

**Agent returning errors?**
```powershell
# Check agent logs for [AGENT_EXEC] entries
docker compose logs agent | Select-String "AGENT_EXEC"

# Test agent directly
$body = '{"tool_name": "run_terminal_command", "parameters": {"command": "echo hello"}}'
Invoke-RestMethod -Uri http://localhost:4001/execute -Method POST -Body $body -ContentType "application/json" -Headers @{"X-Agent-Key"="your_key"}
```

**Session not persisting?**
```python
# Check database directly
import sqlite3
conn = sqlite3.connect("data/proxi.db")
conn.row_factory = sqlite3.Row
sessions = conn.execute("SELECT id, title, updated_at FROM sessions ORDER BY updated_at DESC LIMIT 5").fetchall()
for s in sessions:
    print(dict(s))
```

### SSE Debugging

To inspect raw SSE events from the chat endpoint:

```powershell
# Using curl
curl -N -X POST http://localhost:4000/api/chat `
  -H "Content-Type: application/json" `
  -H "Cookie: session_id=your_session_id" `
  -d '{"message": "hello", "mode": "quick"}'
```

Each line is a JSON object with a `type` field: `llm_thought`, `final_response`, `screenshot`, `approval_request`, `plan`, `goal_update`, `error`, `done`.

---

## Testing

### Manual Testing Checklist

1. **Auth flow**: Login → verify session cookie → access protected endpoint → logout
2. **Chat (quick mode)**: Simple question → verify streaming response
3. **Chat (balanced mode)**: "Check system health" → verify tool execution + response
4. **Approval flow**: "Kill process 1234" → verify approval modal → approve → verify execution
5. **Blocked command**: Try `rm -rf /` → verify BLOCKED response
6. **Agent health**: Check workstation health from UI or API
7. **Session persistence**: Chat → refresh page → verify session loads
8. **Magic link**: Create link (admin) → open in incognito → verify auto-login
9. **Screenshot**: "Take a screenshot" → verify image appears in chat
10. **PowerPoint** (Windows agent): "Open PowerPoint and add a slide" → verify COM automation

### API Testing

```powershell
# Login
$login = Invoke-RestMethod -Uri http://localhost:4000/api/auth/login -Method POST `
  -Body '{"username":"demo","password":"your_password"}' -ContentType "application/json" `
  -SessionVariable session

# Chat
Invoke-RestMethod -Uri http://localhost:4000/api/chat -Method POST `
  -Body '{"message":"hello","mode":"quick"}' -ContentType "application/json" `
  -WebSession $session

# List sessions
Invoke-RestMethod -Uri http://localhost:4000/api/sessions -WebSession $session

# Check agent health
Invoke-RestMethod -Uri http://localhost:4000/api/workstations/linux-container/health -WebSession $session
```

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `GEMINI_API_KEY not found` | Missing `.env` file | Copy `.env.example` to `.env`, add key |
| `No agent selected` | NullDesktopService active | Select a workstation from the UI or register one |
| `Agent unreachable` | Agent not running or wrong IP | Check agent health endpoint, verify network |
| `Import error: pywinauto` | Windows-only package on Linux | Use `requirements-linux.txt` for containers |
| `Screenshot failed` | Headless environment | Agents need a display; use Virtual Display Driver or run natively |
| `PowerPoint COM error` | No PowerPoint installed or no instance | Install Office, open a presentation first |
| `Session expired` | 6-hour default timeout | Re-login or use remember_me |
| `CORS error in browser` | Origin not in allowed list | Add origin to `CORS_ORIGINS` env var |
| `Database locked` | Concurrent write contention | WAL mode should handle this; check for zombie connections |
| `Tool call limit reached` | Mode has low max_tool_calls | Switch to `balanced` (20) or `thorough` (40) mode |

---

*Previous: [Deployment ←](09_deployment.md) | Back to: [Index ←](README.md)*
