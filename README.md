# Proxi: The Headless OS Operator

> **Work while you're on the move.** Control your desktop from your phone.

[![Google Gemini](https://img.shields.io/badge/Powered%20by-Google%20Gemini-4285F4?logo=google)](https://ai.google.dev/)
[![Python 3.12](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)](https://react.dev)

---

## What is Proxi?

Proxi is an **OS-level AI agent** that bridges high-level reasoning (Google Gemini) with low-level execution (Mouse/Keyboard/Vision). Unlike browser-only agents, Proxi can control **any application** on your desktop.

### Key Differentiators

| Feature | Browser Agents | Proxi |
|---------|---------------|-------|
| **Scope** | DOM manipulation only | Full OS control |
| **Legacy Apps** | ❌ | ✅ Notepad, Excel, VPNs |
| **System Control** | ❌ | ✅ Task Manager, Services |
| **Verification** | Trust LLM output | ✅ Independent audit |
| **Mobile Access** | Limited | ✅ Full telepresence |

---

## Quick Start

### Option 1: Windows (Recommended for Desktop Control)

```powershell
# 1. Clone the repository
git clone https://github.com/vermamanoj/proxi-ai.git
cd proxi-ai

# 2. Run setup (as Administrator)
.\setup_windows.ps1

# 3. Edit .env with your API key
notepad .env

# 4. Start the server
.\run_proxi.bat
```

### Option 2: Linux/Docker (Headless Server)

```bash
# 1. Clone and configure
git clone https://github.com/vermamanoj/proxi-ai.git
cd proxi-ai
cp .env.example .env
nano .env  # Add your GEMINI_API_KEY

# 2. Deploy with Docker
./deploy.sh
```

### Option 3: Development Mode

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8080

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

---

## Configuration

Create a `.env` file in the project root:

```ini
# Required
GEMINI_API_KEY=your_gemini_api_key_here

# Optional integrations
GITHUB_TOKEN=your_github_token_here

# Runtime mode (DEMO = safe simulation, REAL = actual control)
RUNTIME_MODE=DEMO
```

### Runtime Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| `DEMO` | Simulated incidents, mock responses | Hackathon demos, safe testing |
| `REAL` | Actual mouse/keyboard/shell control | Production use |

---

## Features

### 🎯 Verifiable Agent (Truth Layer)
Proxi never blindly trusts its own output. Every task goes through:
1. **Assign** - Define goal + success criteria
2. **Execute** - Run tools with transparency
3. **Verify** - Independent system check
4. **Judge** - Pass, retry, or escalate

### 🖥️ Desktop Control (Ghost Mode)
- Mouse clicks, drags, scrolling
- Keyboard typing and hotkeys
- Screenshot + Vision analysis
- Windows UI automation

### 📱 Mobile Telepresence
- Access via any browser
- Voice commands (Gemini Live)
- Real-time status streaming
- Works over Cloudflare Tunnel

### 🔍 Transparency Protocol
The agent explains reasoning before every action:
```
Agent: "I will check system health to assess CPU usage..."
Tool:  get_system_health() → {'cpu_percent': 99.8}
Agent: "CPU critical. Identifying culprit process..."
Tool:  run_terminal_command("top") → ffmpeg at 99.8%
Agent: "Terminating ffmpeg to resolve spike..."
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  FRONTEND (React + Vite)                                │
│  ├── Voice Input (Gemini Live WebRTC)                  │
│  ├── Neural Trace (Real-time thought visualization)    │
│  └── Mission Control (Status dashboard)                │
└─────────────────────────────────────────────────────────┘
                          │ HTTPS/WebSocket
                          ▼
┌─────────────────────────────────────────────────────────┐
│  BACKEND (FastAPI)                                      │
│  ├── GeminiService (AI orchestration, 25 tools)        │
│  ├── Orchestrator (Mission tracking, verification)     │
│  └── DesktopService (Factory: Mock or Real)            │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  DESKTOP (Windows/Linux)                                │
│  ├── PyAutoGUI (Mouse/Keyboard)                        │
│  ├── PyWinAuto (Windows UI Automation)                 │
│  └── psutil (System metrics)                           │
└─────────────────────────────────────────────────────────┘
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat` | POST | Send message, get streaming response |
| `/api/vision` | POST | Analyze uploaded image |
| `/api/missions` | GET | List all missions |
| `/api/missions/{id}` | GET | Get mission details |
| `/api/demo/trigger_chaos` | POST | Simulate CPU incident |
| `/api/demo/reset_chaos` | POST | Clear simulated incident |

---

## Troubleshooting

### Backend won't start
```bash
# Check Python version (need 3.12+)
python --version

# Reinstall dependencies
pip install -r backend/requirements.txt
```

### "API Key Missing" error
- Ensure `.env` file exists in project root
- Check encoding (must be UTF-8, not UTF-16)
- Verify key format: `GEMINI_API_KEY=AIza...`

### Desktop control not working
- Windows: Run as Administrator
- Must be in interactive session (not SSH)
- Check `RUNTIME_MODE=REAL` in `.env`

### Frontend can't connect to backend
- Verify backend is running on port 8080
- Check CORS settings in `main.py`
- Try `http://localhost:8080/api/chat` directly

---

## Documentation

- [BLUEPRINT.md](./BLUEPRINT.md) - System architecture deep dive
- [USER_GUIDE.md](./USER_GUIDE.md) - Comprehensive usage guide

---

## License

MIT License - See [LICENSE](./LICENSE) for details.

---

## Acknowledgments

Built for the **Google Gemini Hackathon** using:
- [Google Gemini API](https://ai.google.dev/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [React](https://react.dev/)
- [PyAutoGUI](https://pyautogui.readthedocs.io/)
