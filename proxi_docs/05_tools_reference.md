# 05 — Tools Reference

## Overview

Proxi exposes 48+ tools to the Gemini model. Tools are registered in `GeminiService._register_tools()` and executed via `tools_map[tool_name](params)`. Each tool is declared with a JSON schema for Gemini's function calling API.

Tools are organized into categories below with their parameters, return values, and execution context.

---

## 1. System & Terminal Tools

### `run_terminal_command`

Execute a shell command on the active agent. Subject to CommandGuard safety checks.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `command` | string | Yes | Shell command to execute |

**Returns**: Command output string, or `APPROVAL_REQUIRED:{id}:{reason}`, or `BLOCKED:{reason}`

**Execution**: Core (guardrail check) → Agent (subprocess execution)

**Notes**:
- Windows: Writes to temp `.ps1` file, runs via `powershell -NonInteractive -ExecutionPolicy Bypass`
- Linux: Runs via `/bin/bash -c`
- Output truncated to 2000 chars
- 45-second timeout (Real), 60-second timeout (Linux)
- GUI apps auto-detected and launched non-blocking with `Start-Process`

### `get_system_health`

Get CPU, memory, disk, and boot time metrics.

| Parameter | None | | |

**Returns**: `{status, cpu_percent, memory_percent, boot_time}` or `{cpu_percent, memory_percent, disk_percent, platform, hostname}` (Linux)

### `get_server_time`

Get current server time.

| Parameter | None | | |

**Returns**: ISO format timestamp string

### `wait_seconds`

Pause execution for a specified duration.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `seconds` | int | Yes | Duration to wait |

**Returns**: Confirmation message

---

## 2. Desktop Automation Tools

### `click_at`

Click at specific screen coordinates.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `x` | int | Yes | X coordinate |
| `y` | int | Yes | Y coordinate |

**Returns**: `"Clicked (x, y)"` or error

### `drag_mouse`

Drag from one point to another.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `start_x` | int | Yes | Start X |
| `start_y` | int | Yes | Start Y |
| `end_x` | int | Yes | End X |
| `end_y` | int | Yes | End Y |

### `type_text`

Type text at current cursor position.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `text` | string | Yes | Text to type |

**Notes**: Uses `pyautogui.write()` with 10ms interval between characters.

### `press_hotkey`

Press a keyboard shortcut.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `keys` | list[string] | Yes | Key names (e.g., `["ctrl", "c"]`) |

### `scroll_page`

Scroll the current page/window.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `direction` | string | Yes | `"up"` or `"down"` |

**Notes**: Scrolls 500 units per call.

---

## 3. Vision & Screen Tools

### `look_at_screen`

Enhanced observation: captures screenshot + UI tree + Set-of-Mark overlay, sends to Gemini Vision for analysis.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `task_context` | string | No | Context about what to look for |

**Returns**: Structured analysis from Gemini Vision describing what's on screen with element references.

**Process**:
1. Calls `get_observation(include_som=True)` on agent
2. Receives raw screenshot, SoM-annotated screenshot, and UI element list
3. Sends SoM screenshot + element list + task context to Gemini Vision model
4. Returns natural language analysis with `[N]` element references

### `share_screenshot`

Capture and send a screenshot to the user in chat.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `caption` | string | No | Description for the screenshot |

**Returns**: `"__SCREENSHOT__:{base64_data}"` — intercepted by SSE handler and sent as image event.

### `ground_and_click`

Find a UI element by natural language description and click it. Uses visual grounding.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `element_description` | string | Yes | Natural language description (e.g., "Submit button") |

**Process**:
1. Try agent-local `/ground` endpoint first (requires `GEMINI_API_KEY` on agent)
2. If unavailable, fall back to Core-side Gemini Vision grounding
3. Click at identified coordinates

**Returns**: Click confirmation with element details and confidence level.

### `get_observation` (Agent-level)

Combine screenshot + accessibility tree + Set-of-Mark overlay.

**Returns**:
```json
{
  "screenshot_base64": "...",
  "som_screenshot_base64": "...",
  "ui_elements": [
    {"id": 1, "text": "OK", "type": "Button", "x": 520, "y": 450, "width": 80, "height": 30}
  ],
  "element_count": 42,
  "screen_size": {"width": 1920, "height": 1080}
}
```

---

## 4. Window Management Tools

### `focus_window`

Bring a window to the foreground by title (partial match).

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `title` | string | Yes | Window title substring |

**Requires**: Windows + PyWinAuto

### `list_windows`

List all visible windows with positions and sizes.

**Returns**: `{"windows": [{"title": "...", "x": 0, "y": 0, "width": 1200, "height": 800}, ...]}`

**Limit**: Max 20 windows returned.

### `get_window_rect`

Get a specific window's position and dimensions.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `title` | string | Yes | Window title substring |

**Returns**: `{"title", "x", "y", "width", "height", "right", "bottom"}`

---

## 5. Browser Tools

### `browser_command`

Execute browser actions via hotkeys.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `action` | string | Yes | One of: `NEW_TAB`, `CLOSE_TAB`, `REFRESH`, `NAVIGATE`, `SEARCH` |
| `url` | string | No | URL for NAVIGATE, or query text for SEARCH |

**Process**: Focuses browser window first (searches for Chrome/Edge/Firefox/Brave), then sends appropriate hotkey.

### `read_page_content`

Read the content of the current page via Ctrl+A → Ctrl+C → clipboard.

**Returns**: Page text (up to 20,000 chars).

### `open_target`

Open a file, folder, or URL.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `target` | string | Yes | File path, folder path, or URL |

**Process**: Uses `webbrowser.open()` for URLs, `os.startfile()` on Windows, `xdg-open` on Linux.

---

## 6. Macro Action Tools

These high-level tools combine multiple low-level operations for efficiency.

### `open_app`

Launch an application by name.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `app_name` | string | Yes | Common app name (e.g., "chrome", "notepad", "powerpoint") |

**Built-in app mappings** (Windows): `chrome` → `start chrome`, `notepad` → `notepad.exe`, `paint` → `mspaint.exe`, `explorer` → `explorer.exe`, `powerpoint` → `start powerpnt`, `excel` → `start excel`, `word` → `start winword`, etc.

### `navigate_app`

Open an application and navigate to a specific section in one call.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `app_name` | string | Yes | Application name |
| `destination` | string | Yes | Where to navigate (e.g., "Settings > Privacy") |

**Notes**: Includes Windows Settings URI shortcuts (e.g., `ms-settings:display`, `ms-settings:network-wifi`).

### `interact_element`

Find a UI element by description and perform an action on it.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `description` | string | Yes | Element description (e.g., "the search box") |
| `action` | string | Yes | Action: `click`, `type`, `right_click`, `double_click` |
| `text` | string | No | Text to type (for `type` action) |

### `fill_form`

Fill multiple form fields in sequence.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `fields` | list[dict] | Yes | `[{"label": "Name", "value": "John"}, ...]` |

### `draw_shape`

Draw shapes in applications like Paint.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `shape` | string | Yes | Shape type: `rectangle`, `circle`, `line`, `arrow` |
| `start_x`, `start_y` | int | Yes | Start coordinates |
| `end_x`, `end_y` | int | Yes | End coordinates |

### `perform_workflow`

Execute a multi-step workflow described in natural language.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `steps` | list[string] | Yes | Ordered list of step descriptions |

---

## 7. PowerPoint Tools

All PowerPoint tools use COM automation via `win32com.client`. They require an active PowerPoint instance on a Windows agent.

### Presentation Management

| Tool | Parameters | Description |
|------|-----------|-------------|
| `ppt_get_active_presentation` | — | Get info about the currently open presentation |
| `ppt_open_presentation` | `file_path` | Open a `.pptx` file |
| `ppt_save_presentation` | `save_as_path` (optional) | Save current presentation |
| `ppt_get_slide_info` | `slide_number` (0=all) | Get slide details (shapes, text, positions) |
| `ppt_goto_slide` | `slide_number` | Navigate to a specific slide |
| `ppt_get_theme_colors` | `slide_number` | Extract theme colors and fonts |

### Slide Operations

| Tool | Parameters | Description |
|------|-----------|-------------|
| `ppt_add_slide` | `after_slide`, `layout` | Add a new slide |
| `ppt_duplicate_slide` | `slide_number` | Duplicate an existing slide (preserves formatting) |
| `ppt_delete_slide` | `slide_number` | Delete a slide |

### Content Editing

| Tool | Parameters | Description |
|------|-----------|-------------|
| `ppt_edit_text` | `slide_number`, `shape_name`, `new_text` | Replace text in a named shape |
| `ppt_add_textbox` | `slide_number`, `text`, `left`, `top`, `width`, `height`, `font_size`, `font_color`, `bold`, `align` | Add a new text box |
| `ppt_format_text` | `slide_number`, `shape_name`, `bold`, `italic`, `font_size`, `font_color` | Format text styling |

### Visual Elements

| Tool | Parameters | Description |
|------|-----------|-------------|
| `ppt_add_picture` | `slide_number`, `image_path`, `left`, `top`, `width` | Insert local image |
| `ppt_add_image_from_url` | `slide_number`, `image_url`, `left`, `top`, `width`, `alt_text` | Insert image from URL |
| `ppt_add_shape` | `slide_number`, `shape_type`, `left`, `top`, `width`, `height`, `text` | Add geometric shape |
| `ppt_add_icon` | `slide_number`, `icon_name`, `left`, `top`, `size`, `color` | Add icon (star, arrow, gear, etc.) |
| `ppt_add_chart` | `slide_number`, `chart_type`, `data`, `left`, `top`, `width`, `height`, `title` | Add chart (column/bar/pie/line) |
| `ppt_add_table` | `slide_number`, `rows`, `cols`, `data`, `left`, `top`, `width` | Add formatted table |
| `ppt_insert_smartart` | `slide_number`, `layout_type`, `items`, `left`, `top`, `width`, `height` | Add SmartArt (process, org chart) |

### Shape Manipulation

| Tool | Parameters | Description |
|------|-----------|-------------|
| `ppt_move_shape` | `slide_number`, `shape_name`, `left`, `top` | Reposition a shape |
| `ppt_resize_shape` | `slide_number`, `shape_name`, `width`, `height` | Resize a shape |
| `ppt_set_shape_style` | `slide_number`, `shape_name`, `fill_color`, `line_color`, `line_weight`, `transparency` | Style a shape |

### High-Level Helpers

| Tool | Parameters | Description |
|------|-----------|-------------|
| `ppt_create_business_slide` | `slide_number`, `title`, `points`, `highlight_point` | Create a complete business slide with bullet points |

---

## 8. Mission & Verification Tools

### `assign_mission`

Create a new verifiable mission.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `goal` | string | Yes | Mission objective |
| `verification_criteria` | string | Yes | JSON string defining how to verify (see Orchestrator docs) |

**Returns**: `{mission_id, status: "ASSIGNED"}`

### `report_execution`

Report that mission execution is complete.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `mission_id` | string | Yes | Mission ID from assign_mission |
| `summary` | string | Yes | What was done |

**Returns**: Updated mission status

### `escalate_to_human`

Escalate a mission to human intervention.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `mission_id` | string | Yes | Mission ID |
| `reason` | string | Yes | Why escalation is needed |

---

## 9. Evidence & Forensics Tools

### `store_evidence`

Store investigation evidence for later retrieval.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `claim` | string | Yes | Brief claim/verdict |
| `evidence_type` | string | Yes | Type: `log`, `process`, `file`, `network`, `screenshot` |
| `data` | string | Yes | Evidence content |

**Returns**: `{evidence_id, claim}`

### `get_evidence`

Retrieve stored evidence by ID.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `evidence_id` | string | Yes | Evidence ID from store_evidence |

### `list_evidence`

List all stored evidence items.

**Returns**: List of `{id, claim, type, timestamp}` entries.

### `render_attack_path`

Generate a Mermaid diagram visualizing an attack chain.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `title` | string | Yes | Diagram title |
| `stages` | list[dict] | Yes | `[{"id": "A", "label": "Phishing Email", "type": "entry"}, ...]` |
| `annotations` | list[string] | No | Additional notes |

**Stage types**: `entry`, `execution`, `persistence`, `c2`, `lateral`, `exfiltration` — each rendered with distinct colors.

---

## 10. Integration Tools

### `send_slack_message` (Mock)

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `channel` | string | Yes | Channel name |
| `message` | string | Yes | Message content |

### `create_linear_ticket` (Mock)

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `title` | string | Yes | Ticket title |
| `description` | string | Yes | Ticket description |
| `priority` | string | No | Priority level |

### `query_knowledge_base` (Mock RAG)

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | Yes | Search query |

### `update_github_file`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `repo` | string | Yes | Repository (owner/name) |
| `path` | string | Yes | File path in repo |
| `content` | string | Yes | New file content |
| `message` | string | Yes | Commit message |

**Requires**: `GITHUB_TOKEN` environment variable.

### `create_github_issue`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `repo` | string | Yes | Repository (owner/name) |
| `title` | string | Yes | Issue title |
| `body` | string | Yes | Issue body |

---

## 11. File Tools

### `save_uploaded_image`

Save a user-uploaded image to the agent filesystem.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file_path` | string | Yes | Destination path on agent |

### `send_file_to_user`

Send a file from the agent to the user's browser for download.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file_path` | string | Yes | File path on agent |

**Returns**: `"__FILE__:{base64_data}:{filename}:{mime_type}"` — intercepted by SSE handler.

---

*Previous: [Agent System ←](04_agent_system.md) | Next: [Security →](06_security.md)*
