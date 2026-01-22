# Proxi: The Headless Operator

Proxi is an agentic, voice-first interface that acts as a remote control for Google Cloud, GitHub, and your local desktop environment. It utilizes Gemini 3 Pro and the Gemini Live API for real-time interaction.

## 🚀 Getting Started

### Prerequisites
*   Node.js 18+
*   Python 3.10+
*   Google Cloud Project with Vertex AI enabled
*   Gemini API Key

### Installation (Linux/Mac)
1.  Run `./setup.sh` to install Docker and dependencies.
2.  Create `.env` with your `GEMINI_API_KEY`.
3.  Run `./deploy.sh` to start the containers.

## 🖥️ Windows Desktop Mode Setup (Ghost Operator)

To use Proxi to control a Windows Server or Desktop:

1.  **Open PowerShell as Administrator.**
2.  Navigate to the project root.
3.  Run the setup script:
    ```powershell
    .\setup_windows.ps1
    ```
4.  This script will:
    *   Install Python dependencies (PyAutoGUI, EasyOCR, etc).
    *   Test if Proxi can move your mouse (GUI Session Check).
    *   Generate a `run_proxi.bat` file.
5.  **Edit the `.env` file** created in the root directory and add your `GEMINI_API_KEY`.
6.  Start the backend:
    ```cmd
    run_proxi.bat
    ```
7.  The backend will listen on `0.0.0.0:8080`.

**Note:** For the Ghost Operator (Desktop Control) to work, you must keep an active RDP session or be logged into the physical console. If you minimize RDP, Windows stops rendering the GUI, and screenshot/mouse commands will fail.

## 🧠 Architecture
*   **Frontend:** React + Vite (WebRTC Voice Client)
*   **Backend:** FastAPI (Python)
*   **AI:** Gemini 3 Pro + Gemini Live API
