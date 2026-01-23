
# PROXI: SYSTEM BLUEPRINT & CONTEXT
**Project Name:** Proxi (The Headless Operator for Google Cloud)
**Date:** Jan 2026
**Target:** Google Gemini 3 Hackathon (Top Prize)

## 1. THE MISSION
To build an agentic, voice-first interface that allows developers to perform "Headless SDLC" tasks (Triage, Ops, Architecture) without looking at a screen. It acts as a remote control for Google Cloud, GitHub, and remote Windows Servers.

## 2. THE TECH STACK (Strict Adherence)
*   **AI Model (The Split Brain):** 
    *   **Voice/Relay:** Gemini 2.5 Flash Native Audio (Frontend). Handles WebRTC I/O and delegates tasks.
    *   **Core Reasoning:** Gemini 3 Pro (Backend). Handles complex logic, tool planning, and code generation.
    *   **Fast Action:** Gemini 3 Flash (Backend). Used for high-speed loops and Vision.
*   **Backend:** Python 3.12+ with **FastAPI**.
*   **Streaming Protocol:** NDJSON (Newline Delimited JSON) for real-time thought streaming.
*   **Orchestration:** Custom Async Generator Loop with **Retry Logic** for robust tool calling.
*   **Frontend (Simulator):** React + Tailwind CSS + Vite.
*   **Desktop Automation:** `pyautogui`, `pywinauto`, `opencv` (OS-Agnostic implementation).
*   **Infrastructure:** Google Cloud Run (Dockerized) OR Windows Server (Bare Metal).
*   **Auth:** GitHub OAuth.

## 3. ARCHITECTURE OVERVIEW

### The Executive Relay Pattern
Proxi uses a **Relay Architecture** to maximize the strengths of different Gemini models.
1.  **The Ear (Gemini 2.5):** Sits in the Frontend. It listens to the user via WebRTC. It has **zero** logic tools. It only has one tool: `delegate_task`.
2.  **The Hand-off:** When the user speaks a command ("Check logs"), Gemini 2.5 calls `delegate_task`.
3.  **The Brain (Gemini 3 Pro):** The Backend receives the text payload. It "thinks" about the problem, plans the execution, and runs the actual tools (GitHub, GCP, Shell).
4.  **The Neural Trace:** The Backend streams these thoughts and tool outputs back to the Frontend in real-time for visualization.
5.  **The Voice:** The Backend returns a final text summary. Gemini 2.5 reads this summary back to the user via the established WebRTC link.

### The Flow
[User Voice] 
    | (WebRTC)
[Frontend: Gemini 2.5 Flash] 
    | (Tool Call: delegate_task)
[Backend: FastAPI]
    | (Gemini 3 Pro Reasoning)
    |---> [Tool: GitHub]
    |---> [Tool: Google Cloud]
    |---> [Tool: Windows Desktop (Ghost Mode)]
    |
[Text Response]
    |
[Frontend: Gemini 2.5 Flash]
    | (TTS)
[User Audio]

## 4. CODING STANDARDS
*   **Async First:** All I/O operations must be `async/await`.
*   **Streaming First:** Endpoints should return `StreamingResponse` where possible to reduce perceived latency.
*   **OS Agnostic:** Desktop tools must gracefully fail or disable themselves if running in a headless Linux environment (Cloud Run).
*   **Type Safety:** Strict Python type hinting (`pydantic.BaseModel`).
*   **Environment:** All secrets must be loaded via `os.getenv()` using `python-dotenv`.

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
*   ✅ Gemini 3 Pro Integration (Backend)
*   ✅ Gemini 2.5 Live Integration (Frontend Relay)
*   ✅ Executive Relay Architecture Implementation
*   ✅ OS-Agnostic Desktop Service (Linux/Windows compatibility)
*   ✅ Robust Error Handling (MALFORMED_FUNCTION_CALL Retry)
*   ✅ Neural Trace Visualization

## 7. RISK ANALYSIS & ROADMAP (Feedback Integration)
*   **Latency Compounding:** The voice->backend->vision->action loop is risk-prone. 
    *   *Mitigation:* Batch tool calls where possible. Introduce "Confidence Skipping" (if LLM is 90% sure, skip Planning phase).
*   **UX Noise:** "Thinking out loud" can be distracting.
    *   *Mitigation:* Added `INTERNAL_MONOLOGUE` toggle in Frontend. Default to "Reflex" mode for users, "Deep" for debugging.
*   **Recovery Primitives:**
    *   *Mitigation:* System prompts now explicitly instruct Gemini 3 to "Self-Correct" if a tool fails ("Last action failed, re-evaluating...").
*   **Planner vs Executor:**
    *   *Mitigation:* Separated logic into "Phase 1: Plan" and "Phase 2: Execution" in the system instruction.
