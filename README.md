
# Proxi: The Headless Operator

**Mission:** To build an agentic, voice-first interface that allows developers to perform "Headless SDLC" tasks (Triage, Ops, Architecture) without looking at a screen. It acts as a remote control for Google Cloud, GitHub, and your local desktop.

## ⚡ Key Features

*   **Executive Relay Architecture:** Combines the low-latency voice capabilities of **Gemini 2.5 Live** with the deep reasoning power of **Gemini 3 Pro**.
*   **Hive Orchestrator:** The backend uses a "Planner-Executor" model. It validates requests against a Knowledge Base, formulates a plan, and then executes it using specialized tools.
*   **Team Productivity:** Integrated with (Mock) **Slack**, **Linear**, and **RAG** (Knowledge Base) to handle real-world workflow tasks like ticketing and communication.
*   **Neural Trace:** Visualize the agent's internal thought process, tool planning, and execution steps in real-time.
*   **OS Agnostic:** 
    *   **Cloud Mode:** Runs on Linux (Docker/Cloud Run) for GitHub & GCP tasks.
    *   **Ghost Mode:** Runs locally on Windows to control mouse/keyboard and see the screen.
*   **Streaming Brain:** The backend streams thoughts and actions via NDJSON, providing immediate feedback.

## 📦 System Modules

Proxi consists of three distinct modules that work in a relay:

### 1. Proxi Console (Frontend / The Ear)
*   **Gemini 2.5 Flash (Native Audio)**: Handles the WebRTC voice connection.
*   **Role**: Acts as a "Secretary". It listens to requests and uses a `delegate_task` tool to hand them off to the Backend.
*   **Visualization**: Renders the "Neural Trace" streamed from the backend.

### 2. Proxi Core (Backend / The Brain)
*   **Gemini 3 Pro**: Acts as the Hive Orchestrator.
*   **Planner Phase**: Breaks complex requests ("Fix production") into atomic steps.
*   **Executor Phase**: Runs tools in parallel where possible.
*   **Tooling**: GitHub, GCP, Desktop, Slack, Linear, Knowledge Base.
*   **Resilience**: Includes auto-retry logic for stochastic LLM tool errors.

### 3. Proxi Ghost (Desktop Agent)
*   **Module**: `desktop_service.py`
*   **Behavior**: Automatically detects the OS.
    *   **Linux/Headless**: Disables GUI tools, runs purely as a Cloud Ops agent.
    *   **Windows**: Enables `pyautogui`, `pywinauto`, and `opencv` for physical desktop control.

---

## 🛠️ Deployment Guide

### Scenario A: Production / Cloud Deployment (Standard)
*Best for: Hosting the full stack (Core + Console) on a Linux server or Google Cloud Run.*

1.  **Setup Environment:**
    Create a `.env` file in the root:
    ```ini
    GEMINI_API_KEY=your_key_here
    GITHUB_TOKEN=your_token_here
    ```

2.  **Run Deployment Script:**
    ```bash
    ./deploy.sh
    ```
    This pulls the latest code, builds Docker images, and configures Nginx.

3.  **Access:**
    *   Frontend: `http://localhost`
    *   Backend API: `http://localhost/api`

---

### Scenario B: Ghost Operator Setup (Windows Local)
*Best for: Controlling a specific Windows machine's desktop.*

**Prerequisites:** Windows 10/11, PowerShell (Admin), Python 3.10+.

1.  **Run Windows Setup:**
    Open PowerShell as Administrator in the project root:
    ```powershell
    .\setup_windows.ps1
    ```
    This creates a Python Virtual Environment (`venv`), installs desktop automation libs (`pyautogui`, `opencv`), and generates a startup script.

2.  **Configuration:**
    Edit the generated `.env` file to add your `GEMINI_API_KEY`.

3.  **Start the Agent:**
    Double-click `run_proxi.bat`. The backend will listen on `0.0.0.0:8080`.

4.  **Unattended Access:**
    Use `disconnect_keep_alive.bat` when exiting RDP to keep the session active and unlocked for the vision agent.

---

## 🎮 Usage

### Voice Commands (Gemini Live)
Click **"INITIATE UPLINK"** on the console.
*   The Frontend (Gemini 2.5) listens.
*   It delegates the intent to the Backend (Gemini 3).
*   The Backend executes tools and returns a summary.
*   The Frontend speaks the summary.

### Text / Vision Mode
Use the terminal input at the bottom.
*   **Text**: "Analyze the system architecture." (Streams thoughts and actions)
*   **Vision**: Click the Camera icon to upload a diagram or screenshot.
*   **Ops**: "Restart the auth service and notify the team on Slack."

## 🏗️ Architecture

```mermaid
graph TD
    User((User Voice)) -->|WebRTC Audio| Front[Frontend: Gemini 2.5 Live]
    Front -->|Tool Call: delegate_task| Back[Backend: FastAPI]
    
    subgraph "The Hive Mind (Gemini 3)"
        Back -->|Consult| RAG[(Knowledge Base)]
        Back -->|Plan & Execute| Logic[Gemini 3 Pro]
        Logic -->|Action Stream| Trace[Neural Trace (NDJSON)]
    end
    
    subgraph "Tool Execution"
        Logic -->|Review PR| GitHub[GitHub API]
        Logic -->|Comms| Slack[Slack / Linear]
        Logic -->|Control Desktop| Ghost{OS Check}
        Ghost -->|Windows| Win[PyAutoGUI/Win32]
        Ghost -->|Linux| Linux[Shell Only]
    end
    
    Trace -->|Visualization| Front
    Logic -->|Text Summary| Back
    Back -->|Response| Front
    Front -->|TTS Audio| User
```
