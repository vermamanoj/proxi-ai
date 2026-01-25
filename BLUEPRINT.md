# PROXI: SYSTEM BLUEPRINT
**Version:** v2.2.0-STABLE  
**Target:** Google Gemini Hackathon ($100k Top Prize)  
**Last Updated:** January 2026

---

## 1. THE MISSION

Proxi is a **Headless OS-Level AI Agent** that lets you work while on the move. It bridges high-level reasoning (Google Gemini) with low-level execution (Mouse/Keyboard/Vision) to automate tasks across Legacy Apps, Browsers, and Systems.

**Core Value Proposition:**
- Work from your phone while your Windows/Linux desktop executes complex tasks
- Full OS control, not just browser DOM manipulation (unlike ByteBot)
- Verifiable agent - proves it fixed the issue before reporting success

---

## 2. TECH STACK

### AI Models
| Role | Model | Purpose |
|------|-------|---------|
| **Fast Reasoning** | `gemini-2.0-flash` | Quick responses, tool execution |
| **Deep Reasoning** | `gemini-2.5-pro-preview-06-05` | Complex multi-step tasks |
| **Vision Analysis** | `gemini-2.0-flash` | Screenshot analysis, UI verification |
| **Voice (Frontend)** | Gemini 2.5 Flash Native Audio | WebRTC voice I/O |

### Backend Stack
- **Language:** Python 3.12+
- **Framework:** FastAPI + Uvicorn
- **SDK:** `google-generativeai` (Stable)
- **Streaming:** NDJSON (Newline Delimited JSON)
- **Database:** SQLite (Mission tracking)

### Desktop Automation
- **Mouse/Keyboard:** PyAutoGUI
- **Windows UI Automation:** PyWinAuto
- **System Metrics:** psutil
- **Vision:** Screenshot → Gemini Vision API
- **Clipboard:** pyperclip

### Frontend
- **Framework:** React 18 + TypeScript
- **Styling:** Tailwind CSS (Cyberpunk theme)
- **Build:** Vite
- **Voice:** Web Speech API + Gemini Live

### Infrastructure
- **Linux Server:** Docker Compose + Nginx
- **Windows Server:** Native Python + Cloudflare Tunnel
- **Production URL:** https://proxi.audista.com

---

## 3. ARCHITECTURE

### 3.1 The Executive Relay Pattern
```
┌─────────────────────────────────────────────────────────────┐
│  MOBILE BROWSER                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Voice Input → Gemini 2.5 Live → delegate_task()     │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼ HTTPS / WebSocket
┌─────────────────────────────────────────────────────────────┐
│  BACKEND (FastAPI)                                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ GeminiService                                        │   │
│  │ ├── System Instruction (Transparency Required)      │   │
│  │ ├── Tool Map (25 tools)                              │   │
│  │ └── Chat Session (Multi-turn with history)          │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Orchestrator (Triple Handshake)                      │   │
│  │ ├── assign_mission(goal, criteria)                  │   │
│  │ ├── report_execution(summary)                       │   │
│  │ └── verify_mission() → Independent System Check     │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Desktop Service (Factory Pattern)                    │   │
│  │ ├── RUNTIME_MODE=DEMO → MockDesktopService          │   │
│  │ └── RUNTIME_MODE=REAL → RealDesktopService          │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 The Truth Layer (Verifiable Agent)
Proxi never blindly trusts LLM output. Every mission goes through:

1. **Assign:** `assign_mission(goal="Fix CPU spike", criteria={"cpu_threshold": 50})`
2. **Execute:** Agent calls tools, explains reasoning before each action
3. **Report:** Agent claims task complete with summary
4. **Verify:** Orchestrator runs independent system check (psutil, HTTP, screenshot)
5. **Judge:** If verification fails, agent retries or escalates to human

### 3.3 Transparency Protocol
The agent MUST explain before every tool call:
```
Agent: "I will check system health to assess CPU usage..."
Tool:  get_system_health() → {'cpu_percent': 99.8, 'status': 'critical'}
Agent: "CPU is critical at 99.8%. I will identify the culprit process..."
Tool:  run_terminal_command("top -bn1") → ffmpeg_transcode at 99.8%
Agent: "Found ffmpeg_transcode consuming CPU. I will terminate it..."
```

---

## 4. FEATURE MAP

| Feature | Implementation | File |
|---------|----------------|------|
| **Desktop Control** | PyAutoGUI + PyWinAuto | `desktop/real.py` |
| **Mock Mode (Demo)** | Simulated incidents | `desktop/mock.py` |
| **Factory Pattern** | RUNTIME_MODE switch | `desktop/factory.py` |
| **Mission Tracking** | SQLite database | `database.py` |
| **Verification** | Independent auditor | `orchestrator.py` |
| **Tool Execution** | 25 registered tools | `gemini_service.py` |
| **Standard Tools** | GitHub, Slack, Linear | `tools/standard_tools.py` |
| **Neural Trace** | Real-time streaming | Frontend `useProxiBrain.ts` |
| **Voice I/O** | Gemini Live WebRTC | Frontend `useGeminiLive.ts` |
| **Session Management** | Multi-turn conversation | Frontend + Backend |
| **Approval Flow** | In-chat destructive action approval | `gemini_service.py` |
| **Chat View** | Mobile-first chat bubbles | `ChatView.tsx` |

---

## 5. TOOL INVENTORY

### System Tools
- `get_system_health` - CPU, memory, boot time
- `run_terminal_command` - Execute shell commands
- `get_server_time` - Current timestamp

### Desktop Tools (Ghost Mode)
- `click_at(x, y)` - Mouse click
- `drag_mouse(start, end)` - Mouse drag
- `type_text(text)` - Keyboard input
- `press_hotkey(keys)` - Keyboard shortcuts
- `scroll_page(direction)` - Scroll up/down
- `look_at_screen(purpose)` - Screenshot + Vision analysis
- `scan_ui_tree()` - Windows accessibility tree
- `open_target(resource)` - Open URL/file
- `read_page_content()` - Extract text from window
- `browser_command(action)` - Browser hotkeys

### Integration Tools
- `send_slack_message(channel, message)`
- `create_linear_ticket(title, priority)`
- `create_github_issue(repo, title, body)`
- `update_github_file(repo, path, content)`
- `query_knowledge_base(query)`

### Orchestration Tools
- `assign_mission(goal, criteria)`
- `report_execution(mission_id, summary)`
- `verify_mission(mission_id)`
- `escalate_to_human(mission_id, reason)`
- `add_item(mission_id, type, source, attributes)`
- `update_item_status(item_id, status)`

---

## 6. DEPLOYMENT MODES

### Mode A: Demo/Hackathon (Safe for Judges)
```env
RUNTIME_MODE=DEMO
```
- Uses `MockDesktopService`
- Simulates CPU spikes, process lists
- No real system changes
- "Trigger Incident" button in UI

### Mode B: Real Operator (Production)
```env
RUNTIME_MODE=REAL
```
- Uses `RealDesktopService`
- Full mouse/keyboard control
- Real shell command execution
- Real screenshot capture

---

## 7. COMPETITIVE ADVANTAGE

| Aspect | ByteBot (Competitor) | Proxi |
|--------|---------------------|-------|
| **Scope** | Browser DOM only | Full OS control |
| **Legacy Apps** | ❌ Cannot control | ✅ Notepad, Excel, VPNs |
| **System Settings** | ❌ | ✅ Task Manager, Services |
| **Verification** | ❌ Trusts LLM output | ✅ Independent audit |
| **Mobile Access** | ❌ | ✅ Work while moving |

---

## 8. RISK MITIGATION

| Risk | Mitigation |
|------|------------|
| **Safety** | Factory Pattern isolates real from mock |
| **Hallucination** | Truth Layer verifies before success |
| **Latency** | Flash model for speed-critical paths |
| **Transparency** | System instruction requires explanation |

---

## 9. CONVERSATION MANAGEMENT

### Session-Based Continuity
Proxi maintains conversation context for multi-turn interactions:

```
Session Created → User asks question → Agent responds
                                      ↓
                        [If approval needed]
                                      ↓
                  Agent asks "Should I proceed?"
                                      ↓
                  User says "yes" → Same session continues
                                      ↓
                        [If new unrelated question]
                                      ↓
                  New session created, separator shown
```

### Trace History
- Conversation history preserved across messages
- Visual separator (`───── New Conversation ─────`) between tasks
- Approval responses continue existing session
- Unrelated questions start fresh context

### Text Input During Speech
- Users can type while TTS is playing
- Submitting cancels ongoing speech
- No blocking during voice output

---

## 10. STATUS

- ✅ Verifiable Agent Architecture
- ✅ Demo Mode (Mock Incidents)
- ✅ Triple Handshake Protocol
- ✅ Real-time Neural Trace
- ✅ Desktop Factory Pattern
- ✅ Transparency Protocol
- ✅ Mobile Telepresence
- ✅ Voice I/O Integration
- ✅ In-Chat Approval Flow
- ✅ Session-Based Conversation Continuity
- ✅ Mobile-First Chat UI
- ✅ Persistent Trace History
