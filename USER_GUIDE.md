# Proxi User Guide

> Complete guide to using Proxi - The Headless OS Operator

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Web Interface](#web-interface)
3. [Voice Commands](#voice-commands)
4. [Text Commands](#text-commands)
5. [Demo Mode](#demo-mode)
6. [Real Mode](#real-mode)
7. [Mobile Access](#mobile-access)
8. [Understanding the Neural Trace](#understanding-the-neural-trace)
9. [Mission System](#mission-system)
10. [Troubleshooting](#troubleshooting)

---

## Getting Started

### Prerequisites

- **Gemini API Key** - Get one at [ai.google.dev](https://ai.google.dev/)
- **Python 3.12+** (for Windows local setup)
- **Docker** (for Linux server deployment)
- **Modern browser** (Chrome, Firefox, Edge)

### First Launch

1. **Start the backend:**
   ```bash
   # Windows
   .\run_proxi.bat
   
   # Linux/Docker
   ./deploy.sh
   ```

2. **Open the web UI:**
   - Local: `http://localhost:5173`
   - Production: `https://proxi.audista.com`

3. **Verify connection:**
   - The status indicator should show "IDLE" (green)
   - Type "hello" and press Enter
   - You should see the agent respond

---

## Web Interface

### Layout Overview

```
┌─────────────────────────────────────────────────────────────┐
│  HEADER: Proxi | Headless Operator                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  NEURAL TRACE                                        │   │
│  │  Shows agent's thoughts, tool calls, and results    │   │
│  │                                                      │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  MISSION CONTROL                                     │   │
│  │  Current mission status and verification results    │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  INPUT AREA                                                 │
│  [Text input] [🎤 Voice] [📎 Upload] [Send]                │
│                                                             │
│  [🔥 TRIGGER INCIDENT]  [Mode: Fast/Deep]                  │
└─────────────────────────────────────────────────────────────┘
```

### Status Indicators

| Status | Color | Meaning |
|--------|-------|---------|
| IDLE | Green | Ready for input |
| PLANNING | Blue | Processing your request |
| EXECUTING | Yellow | Running tools |
| SPEAKING | Blue pulse | Reading response aloud |
| VERIFYING | Purple | Checking results |
| ERROR | Red | Something went wrong |

### Conversation History

Proxi preserves your conversation history within a session:
- Previous messages remain visible as you work
- Visual separators appear between different tasks
- Approval conversations maintain context until resolved
- You can scroll back to review previous actions

---

## Voice Commands

### Enabling Voice

1. Click the **🎤 microphone** button
2. Allow browser microphone access
3. Speak your command
4. Click again to stop recording

### Example Voice Commands

**System Operations:**
- "Check system health"
- "Show me the top CPU processes"
- "How much memory is available?"

**Desktop Control:**
- "Open Notepad and write a Python hello world"
- "Take a screenshot and describe what you see"
- "Click on the Start button"

**Web Browsing:**
- "Open Google Chrome and search for weather"
- "Navigate to github.com"
- "Scroll down on this page"

---

## Text Commands

### Basic Syntax

Simply type what you want Proxi to do. Be specific about:
- **What** you want done
- **Where** it should happen
- **How** to verify success

### Command Examples

#### System Monitoring
```
Check system health and tell me if anything looks wrong
```

```
Find the top 3 memory-intensive processes
```

```
What processes are using more than 50% CPU?
```

#### File Operations
```
Create a new text file on the desktop called notes.txt with today's date
```

```
Open the Downloads folder and list all PDF files
```

#### Web Tasks
```
Open Chrome, go to news.google.com, and summarize the top headlines
```

```
Search for "Python FastAPI tutorial" and open the first result
```

#### Complex Multi-Step
```
There's a high CPU alert. Check system health, identify the culprit, and fix it.
```

```
Open VS Code, create a new Python file, write a function to calculate fibonacci, and save it.
```

#### PowerPoint Editing

Proxi can edit PowerPoint presentations while preserving organization themes and formatting.

**Basic Operations:**
```
Open presentation.pptx and tell me what slides it has
```

```
Go to slide 3 and read the content
```

**Theme-Aware Content Creation:**
```
Open deck.pptx, look at slides 2-3 for the theme style, then create 3 new slides about LLM Security
```

**Visual Editing:**
```
Add a picture from C:/images/logo.png to slide 1 in the top right corner
```

```
Add a blue arrow shape pointing right on slide 5
```

**Available PPT Tools:**

| Tool | Description |
|------|-------------|
| `ppt_open_presentation` | Open a .pptx file |
| `ppt_get_slide_info` | Read slide structure and text |
| `ppt_edit_text` | Edit text preserving formatting |
| `ppt_add_slide` | Add new slide with theme layout |
| `ppt_duplicate_slide` | Clone slide (best for theme preservation) |
| `ppt_delete_slide` | Remove a slide |
| `ppt_add_picture` | Insert image at position |
| `ppt_add_shape` | Add shapes (rectangle, oval, arrow, etc.) |
| `ppt_move_shape` | Reposition shapes |
| `ppt_resize_shape` | Resize shapes |
| `ppt_format_text` | Bold, italic, size, color |
| `ppt_get_theme_colors` | Extract theme colors and fonts |
| `ppt_save_presentation` | Save changes |

**Note:** PowerPoint must be installed. Works via COM automation (no admin required).

---

## Demo Mode

Demo mode (`RUNTIME_MODE=DEMO`) is safe for testing and demonstrations. It simulates system state without making real changes.

### Triggering a Demo Incident

1. Click **🔥 TRIGGER INCIDENT** button
2. This simulates a CPU spike (99.8%)
3. Ask Proxi to fix it:
   ```
   There's a CPU alert. Diagnose and fix the issue.
   ```

### What Happens in Demo Mode

| Action | Real Mode | Demo Mode |
|--------|-----------|-----------|
| `get_system_health` | Real CPU/Memory | Simulated values |
| `run_terminal_command` | Executes on OS | Returns mock output |
| `click_at` | Moves real mouse | Returns "Click simulated" |
| `look_at_screen` | Real screenshot | Mock description |

### Demo Flow Example (with Approval)

```
You: "There's a CPU spike. Fix it."

Agent: "I will check system health to assess the situation..."
Tool:  get_system_health → {'cpu_percent': 99.8, 'status': 'critical'}

Agent: "CPU is critical. Identifying the culprit process..."
Tool:  run_terminal_command("ps aux") → ffmpeg (PID 1337) at 99.8%

Agent: "I found the issue:
  Process: ffmpeg (PID 1337)
  Usage: 99.8% CPU, 45% Memory
  Task: Video transcoding - converting wedding_video.mp4
  Impact if killed: Low - batch job can be restarted
  
  Should I proceed? Reply 'yes' to approve or 'no' to cancel."

You: "yes"

Agent: "Terminating process 1337..."
Tool:  run_terminal_command("kill 1337") → Process terminated

Agent: "Verifying fix..."
Tool:  get_system_health → {'cpu_percent': 15.4, 'status': 'online'}

Agent: "Done! Process 1337 has been killed. CPU is now at 15.4% (normal).
        I've also notified the ops team on Slack."
```

### Approval Flow

For destructive actions (killing processes, deleting files, system changes), Proxi will:

1. **Diagnose** - Identify the issue and gather details
2. **Present Options** - Show detailed info about the proposed action
3. **Request Approval** - Ask for explicit user confirmation
4. **Execute** - Only proceed after receiving "yes"
5. **Verify** - Check that the action succeeded
6. **Confirm** - Report final status to user

**Approval Keywords:** `yes`, `no`, `proceed`, `cancel`, `approve`, `deny`

---

## Real Mode

Real mode (`RUNTIME_MODE=REAL`) gives Proxi actual control of your system.

### ⚠️ Safety Warnings

- Proxi can move your mouse and type on your keyboard
- Proxi can execute shell commands
- Proxi can open/close applications
- Always monitor what Proxi is doing
- Keep the Neural Trace visible

### Enabling Real Mode

1. Edit `.env` file:
   ```ini
   RUNTIME_MODE=REAL
   ```

2. Restart the backend:
   ```bash
   # Windows
   Ctrl+C in run_proxi.bat window
   .\run_proxi.bat
   ```

### Real Mode Capabilities

| Tool | What It Does |
|------|--------------|
| `click_at(x, y)` | Clicks at screen coordinates |
| `type_text(text)` | Types using keyboard |
| `press_hotkey(keys)` | Presses key combinations |
| `drag_mouse(start, end)` | Drags between points |
| `scroll_page(direction)` | Scrolls up/down |
| `run_terminal_command(cmd)` | Executes in PowerShell/Bash |
| `open_target(resource)` | Opens URL or file |
| `look_at_screen(purpose)` | Screenshots + analyzes |
| `scan_ui_tree()` | Gets Windows UI elements |

---

## Mobile Access

Proxi is designed for mobile telepresence - control your desktop while on the move.

### Option 1: Local Network

If your phone and computer are on the same network:

1. Find your computer's IP: `ipconfig` (Windows) or `ip addr` (Linux)
2. Open on phone: `http://192.168.x.x:5173`

### Option 2: Cloudflare Tunnel (for testing

For access from anywhere:

1. Install cloudflared:
   ```bash
   # Windows
   winget install cloudflare.cloudflared
   
   # Linux
   curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o cloudflared
   chmod +x cloudflared
   ```

2. Create tunnel:
   ```bash
   cloudflared tunnel --url http://localhost:5173
   ```

3. Use the generated URL on your phone

### Mobile Tips

- Use voice commands for easier input
- Enable "Desktop site" in browser for full UI
- Keep screen on during long operations
- Check Neural Trace for progress

---

## Understanding the Neural Trace

The Neural Trace shows Proxi's internal reasoning process.

### Message Types

| Type | Icon | Description |
|------|------|-------------|
| **Thought** | 💭 | Agent's reasoning before action |
| **Tool Call** | ⚡ | Tool being executed |
| **Tool Result** | 📋 | Output from tool |
| **Response** | 💬 | Final response to user |
| **Error** | ❌ | Something went wrong |
| **Verification** | ✅/❌ | Mission verification result |

### Reading the Trace

```
💭 THOUGHT: "I will check system health to assess CPU usage..."
   ↓
⚡ TOOL: get_system_health()
   ↓
📋 RESULT: {'cpu_percent': 45.2, 'memory_percent': 62.1}
   ↓
💭 THOUGHT: "System looks healthy. CPU at 45%, memory at 62%."
   ↓
💬 RESPONSE: "Your system is healthy. No issues detected."
```

---

## Mission System

For complex tasks, Proxi uses a mission system to track progress and verify results.

### Mission Lifecycle

```
ASSIGNED → EXECUTING → VERIFYING → VERIFIED/FAILED
```

### Mission Components

1. **Goal**: What needs to be accomplished
2. **Criteria**: How to measure success
3. **Evidence**: System state collected during verification
4. **Judgment**: Pass/fail determination

### Example Mission

```json
{
  "id": "abc123",
  "goal": "Fix high CPU usage",
  "criteria": {
    "metric": "cpu",
    "threshold": 50
  },
  "status": "VERIFIED",
  "evidence": {
    "cpu_percent": 15.4,
    "status": "online"
  }
}
```

### Viewing Missions

Missions are displayed in the **Mission Control** panel. You can also query via API:

```bash
curl http://localhost:8080/api/missions
```

---

## Troubleshooting

### Common Issues

#### "API Key Missing"
- Check `.env` file exists in project root
- Verify format: `GEMINI_API_KEY=AIza...`
- Ensure UTF-8 encoding (not UTF-16)

#### Agent Not Responding
- Check backend terminal for errors
- Verify network connectivity
- Try refreshing the page

#### Tools Not Working
- Confirm `RUNTIME_MODE` setting
- Check if running as Administrator (Windows)
- Verify not running via SSH (need GUI session)

#### Voice Not Working
- Allow microphone permissions in browser
- Use HTTPS (required for microphone in most browsers)
- Try a different browser

### Getting Help

1. Check the backend terminal for error messages
2. Look at Neural Trace for failure points
3. Review `backend/logs/` if logging is enabled

### Resetting State

If things get stuck:

```bash
# Stop backend
Ctrl+C

# Clear database (missions)
rm backend/proxi.db

# Restart
.\run_proxi.bat
```

---

## Best Practices

### Writing Good Commands

✅ **Good:**
```
Check system health and create a Linear ticket if CPU is above 80%
```

❌ **Vague:**
```
Check things
```

### For Complex Tasks

1. Be specific about success criteria
2. Break into smaller steps if needed
3. Monitor the Neural Trace
4. Let verification complete before new commands

### Security

- Don't share your API keys
- Use Demo mode for public demonstrations
- Monitor Real mode operations closely
- Review commands before sending in Real mode

---

## Quick Reference

### Keyboard Shortcuts (Web UI)

| Shortcut | Action |
|----------|--------|
| Enter | Send message |
| Ctrl+M | Toggle microphone |
| Escape | Cancel current input |

### API Quick Reference

```bash
# Send chat message
curl -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "check system health"}'

# Trigger demo incident
curl -X POST http://localhost:8080/api/demo/trigger_chaos

# Reset demo incident
curl -X POST http://localhost:8080/api/demo/reset_chaos

# List missions
curl http://localhost:8080/api/missions
```

---

*For technical details, see [BLUEPRINT.md](./BLUEPRINT.md)*
