# 04 — Agent System

## Overview

Proxi Agents are lightweight, isolated FastAPI servers that execute desktop operations on behalf of Proxi Core. They have **no access** to user databases, sessions, or API keys (except optionally `GEMINI_API_KEY` for local visual grounding).

Key files:

| File | Lines | Purpose |
|------|-------|---------|
| `backend/agent_server.py` | 679 | FastAPI agent server with tool dispatch |
| `backend/services/desktop/interface.py` | 206 | Abstract base class for all desktop services |
| `backend/services/desktop/factory.py` | 73 | Factory pattern for service selection |
| `backend/services/desktop/real.py` | 701 | Windows desktop automation (PyAutoGUI + PyWinAuto) |
| `backend/services/desktop/linux.py` | 191 | Linux terminal-only operations |
| `backend/services/desktop/proxy_adapter.py` | 277 | HTTP proxy to remote agents |
| `backend/services/desktop/null.py` | 139 | Safety net — blocks all ops when no agent |
| `backend/services/desktop/mock.py` | 148 | Demo mode with simulated responses |

---

## Agent Server (`agent_server.py`)

### Startup

```
uvicorn backend.agent_server:app --host 0.0.0.0 --port 8081
```

On startup:
1. Loads `.env` from multiple locations (repo root, script dir, cwd)
2. Configures `PROXI_AGENT_KEY` for authentication
3. Creates FastAPI app with permissive CORS
4. Uses `get_desktop_service(allow_local=True)` — always executes locally

### Endpoints

#### Health & Info

| Endpoint | Method | Auth | Response |
|----------|--------|------|----------|
| `/` | GET | None | Service name, status, platform, hostname |
| `/health` | GET | Agent Key | System metrics (CPU, memory, disk) |
| `/capabilities` | GET | None | List of available tool categories |

#### Tool Execution

| Endpoint | Method | Auth | Response |
|----------|--------|------|----------|
| `/execute` | POST | Agent Key | `{success, result, error}` |

The `/execute` endpoint maps `tool_name` to local desktop service methods via a large if/elif dispatch block. Supported tools:

**System**: `run_terminal_command`, `get_system_health`, `open_target`, `wait_seconds`

**Mouse/Keyboard**: `click_at`, `drag_mouse`, `type_text`, `press_hotkey`

**Screen**: `get_screenshot_base64`, `get_observation`, `scan_ui_tree`

**Window**: `focus_window`, `list_windows`, `get_window_rect`

**Browser**: `read_page_content`, `scroll_page`, `browser_command`

**PowerPoint** (20+ tools): `ppt_get_active_presentation`, `ppt_open_presentation`, `ppt_get_slide_info`, `ppt_edit_text`, `ppt_add_slide`, `ppt_duplicate_slide`, `ppt_delete_slide`, `ppt_save_presentation`, `ppt_goto_slide`, `ppt_add_picture`, `ppt_add_shape`, `ppt_move_shape`, `ppt_resize_shape`, `ppt_format_text`, `ppt_get_theme_colors`, `ppt_add_table`, `ppt_add_textbox`, `ppt_set_shape_style`, `ppt_create_business_slide`, `ppt_add_chart`, `ppt_add_image_from_url`, `ppt_add_icon`, `ppt_insert_smartart`

#### Visual Grounding

| Endpoint | Method | Auth | Response |
|----------|--------|------|----------|
| `/ground` | POST | Agent Key | `{action, x, y, element_id, confidence, reasoning}` |

The `/ground` endpoint enables **agent-local visual grounding** — the agent captures a screenshot, overlays Set-of-Mark numbered boxes, and uses a local Gemini model to find the UI element matching a natural language query. This eliminates the round-trip to Core for screen interpretation.

Requires `GEMINI_API_KEY` on the agent. Falls back gracefully if not configured.

#### File Transfer

| Endpoint | Method | Auth | Constraints |
|----------|--------|------|-------------|
| `/files/download` | POST | Agent Key | Max 50MB, base64 encoded |
| `/files/upload` | POST | Agent Key | Restricted to `~/` or `/tmp` |

#### Demo Tools

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/demo/trigger_incident` | POST | Simulate high-CPU incident |
| `/demo/resolve_incident` | POST | Clear simulated incident |

### Request Logging

Every `/execute` call is logged with:
- Unique request ID (8-char hex)
- Tool name
- Sanitized parameters (secrets redacted)
- Execution time in milliseconds
- Success/failure status
- Result preview (truncated to 220 chars)

```
[AGENT_EXEC] START id=a1b2c3d4 tool=run_terminal_command params={"command":"ls -la"}
[AGENT_EXEC] END id=a1b2c3d4 tool=run_terminal_command ok=1 ms=125 result=SUCCESS:\ntotal 48...
```

### Authentication

```python
async def verify_agent_key(x_agent_key: Optional[str] = Header(None)):
    if AGENT_API_KEY and x_agent_key != AGENT_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing agent key")
    return True
```

If `PROXI_AGENT_KEY` env var is set, all endpoints (except `/` and `/capabilities`) require the matching `X-Agent-Key` header.

---

## Desktop Service Layer

### Interface (`desktop/interface.py`)

Abstract base class defining 30+ methods every desktop service must implement:

```python
class DesktopInterface(ABC):
    # System
    @abstractmethod
    def get_system_health(self) -> dict: ...
    @abstractmethod
    def run_terminal_command(self, command: str) -> str: ...
    @abstractmethod
    def open_target(self, resource: str) -> str: ...
    @abstractmethod
    def wait_seconds(self, seconds: int) -> str: ...

    # Input
    @abstractmethod
    def click_at(self, x: int, y: int) -> str: ...
    @abstractmethod
    def drag_mouse(self, sx, sy, ex, ey) -> str: ...
    @abstractmethod
    def type_text(self, text: str) -> str: ...
    @abstractmethod
    def press_hotkey(self, keys: list) -> str: ...

    # Screen
    @abstractmethod
    def get_screenshot_base64(self) -> str: ...
    @abstractmethod
    def get_observation(self, include_som: bool) -> dict: ...
    @abstractmethod
    def scan_ui_tree(self) -> str: ...

    # Window
    @abstractmethod
    def focus_window(self, title: str) -> str: ...
    @abstractmethod
    def list_windows(self) -> dict: ...
    @abstractmethod
    def get_window_rect(self, title: str) -> dict: ...

    # Browser
    @abstractmethod
    def read_page_content(self) -> str: ...
    @abstractmethod
    def scroll_page(self, direction: str) -> str: ...
    @abstractmethod
    def browser_command(self, action: str, url: str) -> str: ...

    # PowerPoint (20+ methods)
    @abstractmethod
    def ppt_get_active_presentation(self) -> str: ...
    # ... (see interface.py for complete list)
```

### Factory (`desktop/factory.py`)

```python
def get_desktop_service(allow_local=False) -> DesktopInterface:
    # 1. If allow_local=True (agent server), return local implementation
    if allow_local:
        if platform == "Linux":
            return LinuxDesktopService()
        else:
            return RealDesktopService()

    # 2. If active agent URL is set, return proxy
    if _active_agent_url:
        return ProxyDesktopService(_active_agent_url)

    # 3. No agent → NullDesktopService (blocks everything)
    return NullDesktopService()
```

The factory also exposes:
- `set_active_agent(url, key)` — Configure which agent to proxy to
- `clear_active_agent()` — Reset to NullDesktopService

---

### Implementation: RealDesktopService (`desktop/real.py`)

> **Naming history:** During early development, Proxi ran as a monolith on a single Windows server with no remote agents. `MockDesktopService` was created first for demo/testing without a real desktop. When actual Windows automation was added later, it was named `RealDesktopService` to distinguish it from mock — the name stuck even after the architecture evolved to a split model.

The Windows desktop automation implementation. 701 lines covering full OS control.

#### Dependencies
- **PyAutoGUI** — Mouse clicks, keyboard input, screenshots
- **PyWinAuto** — Windows UI Automation (accessibility tree, window management)
- **OpenCV** — Image processing, screenshot scaling, Set-of-Mark overlay rendering
- **pyperclip** — Clipboard read/write for page content extraction
- **psutil** — System health metrics

#### Key Features

**Thread-safe input**: All mouse/keyboard operations use `threading.Lock` to prevent race conditions:
```python
with self._input_lock:
    pyautogui.moveTo(x, y, duration=0.1)
    pyautogui.click()
```

**DPI awareness**: Sets `SetProcessDPIAware()` on Windows to ensure coordinate accuracy.

**Screenshot optimization**: Scales to max 1920px width, JPEG quality 50 for manageable base64 size.

**Set-of-Mark (SoM) overlay**: `get_observation()` combines:
1. Raw screenshot capture
2. UI accessibility tree scan (via PyWinAuto)
3. Green numbered bounding boxes drawn on screenshot for each interactive element
4. Returns both raw and annotated screenshots plus element list

**Accessibility tree scanning**: Two variants:
- `_scan_accessibility_tree()` — Basic: text, type, center x/y (max 60 elements)
- `_scan_accessibility_tree_with_bounds()` — Full: includes width/height for SoM boxes (max 80 elements)

**Browser control**: `browser_command()` focuses browser window first, then sends hotkeys (Ctrl+T, Ctrl+W, F5, Ctrl+L+URL+Enter, Ctrl+F+query).

**Security**: Local command blocking for dangerous patterns (separate from Core's CommandGuard):
```python
BLOCKED_PATHS = ['/etc/shadow', 'c:\\windows\\system32\\config\\sam', ...]
BLOCKED_PATTERNS = ['rm -rf /', 'chmod 777', 'curl|bash', ':(){:|:&};:', ...]
```

**GUI app detection**: Recognizes GUI apps (`mspaint`, `notepad`, `chrome`, etc.) and launches them non-blocking with `Start-Process`.

**PowerPoint delegation**: All PPT methods delegate to `backend/tools/ppt_tools.py` functions via local import.

---

### Implementation: LinuxDesktopService (`desktop/linux.py`)

Terminal-only implementation for Linux containers/servers. 191 lines.

**Available**: `run_terminal_command`, `get_system_health`, `open_target` (file read), `wait_seconds`

**Not available** (returns `"not_available"` message): All GUI operations — click, type, screenshot, scan_ui_tree, browser, window management, PowerPoint.

Terminal commands run via `subprocess.run()` with 60-second timeout.

---

### Implementation: ProxyDesktopService (`desktop/proxy_adapter.py`)

Routes all desktop calls to a remote agent via HTTP. 277 lines.

```python
class ProxyDesktopService(DesktopInterface):
    def __init__(self, agent_url, agent_key=""):
        self.agent_url = agent_url
        self.agent_key = agent_key

    def _execute_sync(self, tool_name, params):
        # Async HTTP POST → agent_url/execute
        # Bridged to sync via ThreadPoolExecutor + asyncio.run()
        payload = {"tool_name": tool_name, "parameters": params}
        headers = {"X-Agent-Key": self.agent_key}
        response = requests.post(f"{self.agent_url}/execute", json=payload, headers=headers)
        return response.json()["result"]
```

Every interface method calls `_execute_sync(tool_name, params_dict)` which handles the HTTP round-trip with timeout (30s) and error handling.

---

### Implementation: NullDesktopService (`desktop/null.py`)

Safety net that blocks all operations. 139 lines. **Actively used** — this is the default service returned by the factory when no agent is selected.

Every method returns: `"Error: No agent selected. Please select a workstation first from the Workstation panel."`

Used by Core when no active agent is configured (i.e., user hasn't selected a workstation in the UI yet). This ensures desktop tools can never accidentally execute locally on the Core server. The factory logs `"No agent URL set, returning NullDesktopService"` when this fallback is triggered.

---

### Implementation: MockDesktopService (`desktop/mock.py`)

Demo/simulation mode. 148 lines.

Features:
- Simulated incident: `trigger_incident()` sets CPU to 99.8%, `resolve_incident()` resets
- Mock process list with ffmpeg high-CPU scenario
- Kill command simulation (PID 1337 resolves the incident)
- 1x1 pixel screenshots (red=incident, green=normal)
- Mock UI tree, browser, window operations

---

## Tool Execution Chain (Complete)

```
User: "Kill the high-CPU process"
  │
  ▼
GeminiService.route_and_execute_stream()
  │
  ├─ Gemini model generates: run_terminal_command("taskkill /PID 1337 /F")
  │
  ├─ GeminiService.run_terminal_command("taskkill /PID 1337 /F")
  │   │
  │   ├─ CommandGuard.check_command_safety()
  │   │   └─ Result: NEEDS_APPROVAL (matches "taskkill" pattern)
  │   │
  │   └─ Returns: "APPROVAL_REQUIRED:abc123:Killing a process requires approval"
  │
  ├─ SSE event: {type: "approval_request", id: "abc123", command: "taskkill /PID 1337 /F"}
  │
  ├─ User approves via UI → POST /api/approve/abc123
  │
  ├─ GeminiService.approve_command("abc123")
  │   │
  │   ├─ get_desktop_service() → ProxyDesktopService
  │   │
  │   └─ proxy._execute_sync("run_terminal_command", {command: "taskkill /PID 1337 /F"})
  │       │
  │       └─ HTTP POST agent:8081/execute
  │           │
  │           └─ agent_server.py → ds.run_terminal_command("taskkill /PID 1337 /F")
  │               │
  │               └─ subprocess.run(["powershell", ...]) → "SUCCESS"
  │
  └─ Result returned to Gemini model for next turn
```

---

*Previous: [Backend Services ←](03_backend_services.md) | Next: [Tools Reference →](05_tools_reference.md)*
