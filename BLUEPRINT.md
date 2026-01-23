
# PROXI: SYSTEM BLUEPRINT & CONTEXT
**Project Name:** Proxi (The Headless Operator for Google Cloud)
**Date:** Jan 2026
**Target:** Google Gemini 3 Hackathon (Top Prize)

## 1. THE MISSION
To build an agentic, voice-first interface that allows developers to perform "Headless SDLC" tasks (Triage, Ops, Architecture) without looking at a screen. It acts as a remote control for Google Cloud, GitHub, and remote Windows Servers.

## 2. THE TECH STACK (Strict Adherence)
*   **AI Model:** 
    *   **Reasoning:** Gemini 3 Pro (via Vertex AI).
    *   **Fast Action:** Gemini 3 Flash (for high-speed loops).
    *   **Voice:** Gemini Live API (Real-time WebRTC).
*   **Backend:** Python 3.12+ with **FastAPI**.
*   **Streaming Protocol:** NDJSON (Newline Delimited JSON) for real-time thought streaming.
*   **Orchestration:** Custom Async Generator Loop (supports Parallel Tool Execution).
*   **Database:** 
    *   *Vector:* Pinecone (for Code RAG).
    *   *Session:* In-memory / Redis.
*   **Frontend (Simulator):** React + Tailwind CSS + Vite.
*   **Desktop Automation:** `pyautogui`, `pywinauto`, `opencv` (for Ghost Mode).
*   **Infrastructure:** Google Cloud Run (Dockerized) OR Windows Server (Bare Metal).
*   **Auth:** GitHub OAuth.

## 3. ARCHITECTURE OVERVIEW

### The Streaming Brain
Unlike standard request/response chatbots, Proxi uses a **Streaming Architecture**.
1.  **User Input** -> Sent to Backend.
2.  **Generator Loop** -> Backend yields chunks of data immediately:
    *   `{"type": "llm_thought", "content": "I need to check the logs..."}`
    *   `{"type": "tool_call", "name": "check_gcp_logs"}`
3.  **Parallel Execution** -> If the LLM requests multiple tools (e.g., check logs AND check PRs), Proxi executes them via `asyncio.gather` for minimal latency.
4.  **Trace Visualization** -> The Frontend renders these chunks as a "Neural Trace", allowing the user to see the agent "thinking" in real-time.

### The Flow
[Client: Web/Mobile] <===(WebRTC Audio / NDJSON Stream)===> [Backend: FastAPI]
                                                                    |
                                                          [Async Generator Loop]
                                                                    |
                                        -----------------------------------------------------------
                                        |                   |                     |               |
                                 [Tool: GitHub]     [Tool: Google Cloud]  [Tool: Shell]    [Tool: Vision]
                                 (Parallel Exec)    (Parallel Exec)       (PowerShell)     (Gemini 3 Flash)

## 4. CODING STANDARDS
*   **Async First:** All I/O operations must be `async/await`.
*   **Streaming First:** Endpoints should return `StreamingResponse` where possible to reduce perceived latency.
*   **Plain Text Audio:** LLM responses must be stripped of Markdown before being sent to TTS/Audio generation.
*   **Type Safety:** Strict Python type hinting (`pydantic.BaseModel`).
*   **Environment:** All secrets must be loaded via `os.getenv()` using `python-dotenv`.
*   **Modularity:** Keep "Tools" separate from "Agent Logic".

## 5. CAPABILITIES

### A. Headless Ops (Standard)
*   "Check the logs for service X."
*   "Restart the pod."
*   "List open PRs."

### B. Ghost Operator (Windows)
*   **Hybrid Vision:**
    1.  Tries **Windows Accessibility API** (Text-based, fast).
    2.  If that fails, takes a **Screenshot**.
    3.  Sends screenshot to **Gemini 3 Flash Vision API**.
    4.  LLM decides where to click based on visual coordinate mapping.
*   **Safety:** Prioritizes `PowerShell` over mouse clicking to avoid UI flakiness.

## 6. SPRINT STATUS
*   ✅ FastAPI Server & Streaming Endpoint
*   ✅ Gemini 3 Pro Integration
*   ✅ Parallel Tool Execution Engine
*   ✅ Neural Trace Visualization (Frontend)
*   ✅ Windows Ghost Mode (Local Execution)
*   ✅ WebRTC Audio Uplink (Gemini Live)
