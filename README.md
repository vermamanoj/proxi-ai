
# Proxi: The Headless Operator (v2.1.0-GHOST)

**Mission:** To build an agentic, voice-first interface that allows developers to perform "Headless SDLC" tasks (Triage, Ops, Architecture) without looking at a screen. It acts as a **Verifiable** remote control for Google Cloud, GitHub, and your local desktop.

## ⚡ Key Features

*   **Executive Relay (Hierarchical Agents):** Combines the low-latency voice capabilities of **Gemini 2.5 Live** (The Secretary) with the deep reasoning power of **Gemini 3 Pro** (The Executive).
*   **Reasoning Engine:** Powered by the new **Google GenAI SDK** with native "Thinking" support. Proxi deliberates on complex tasks, showing its internal monologue before taking action.
*   **The Truth Layer:** Proxi implements a "Verifiable Agent" architecture. It defines mathematical success criteria (CPU < 50%, HTTP 200 OK) and independently audits the agent's work before reporting success.
*   **Desktop Control (The Ghost):** Full control over mouse, keyboard, and screen using `pyautogui` and `pywinauto`. Safe-guarded behind a "Real Mode" flag.
*   **Neural Trace:** Visualize the agent's internal thought process, tool planning, and execution steps in real-time.

---

## 🎮 Modes of Operation

Proxi uses a **Factory Pattern** to switch between Safe Demo functionality and Real System Control.

### Option A: Hackathon / Demo Mode (Default)
Safe for public testing. Mocks critical incidents and system state.
1.  Set `RUNTIME_MODE=DEMO` in `.env`.
2.  Use the **"🔥 TRIGGER INCIDENT"** button in the web UI to simulate outages.
3.  The agent will "fix" the simulated `ffmpeg` process without touching your real OS.

### Option B: Real Operator Mode (Production)
**WARNING:** This gives the AI control of your mouse and keyboard.
1.  Set `RUNTIME_MODE=REAL` in `.env`.
2.  **Capabilities Unlocked:**
    *   `click_at`, `type_text`, `drag_mouse` (via PyAutoGUI).
    *   `scan_ui_tree` (via PyWinAuto - Windows Only).
    *   `run_terminal_command` (Executes real PowerShell/Bash).
    *   `look_at_screen` (Takes real screenshots -> Gemini Vision).

---

## 🏗️ Architecture

### 1. The Executive Relay (Hierarchy)
We strictly separate concerns to minimize latency and maximize intelligence:
*   **Frontend (The Ear):** Gemini 2.5 Flash Native Audio. 
    *   *Job:* Low-latency conversation.
    *   *Tools:* Only `delegate_task`. It cannot touch the system directly.
*   **Backend (The Brain):** Gemini 3 Pro.
    *   *Job:* Reasoning, Planning, Tool Execution.
    *   *Tools:* GCP, GitHub, Desktop Control.

### 2. The Truth Layer (Verification)
Proxi never blindly trusts the LLM.
1.  **Assign**: The Brain defines a Goal + Verification Criteria (e.g., "Login button must be visible").
2.  **Execute**: The Brain attempts to fix the issue.
3.  **Verify**: The Orchestrator runs an independent check (Screenshot analysis or HTTP request).

### 3. The Ghost (Desktop Abstraction)
*   **Real Implementation**: `desktop/real.py` (PyAutoGUI, OpenCV).
*   **Mock Implementation**: `desktop/mock.py` (Simulated State).

---

## 🔧 Troubleshooting

### Backend Hanging?
If the Neural Trace stops updating or "hangs" after a thought:
1.  **Check Terminal Output:** Proxi v2.1.0+ includes timeouts. If Gemini 3 Pro takes longer than 35s, it will timeout and report the error to the frontend.
2.  **Malformed Calls:** If you see "Healing malformed call" logs, the system is auto-retrying. If it fails twice, it will abort to prevent infinite loops.
3.  **Restart Backend:** `Ctrl+C` the `run_proxi.bat` window and start it again to clear any stuck threads.

---

## 🛠️ Deployment

1.  **Setup Environment:**
    Create a `.env` file in the root:
    ```ini
    GEMINI_API_KEY=your_key_here
    GITHUB_TOKEN=your_token_here
    RUNTIME_MODE=DEMO  # Change to REAL to enable mouse/keyboard control
    ```

2.  **Run Deployment Script:**
    ```bash
    ./deploy.sh
    ```
