
# PROXI: SYSTEM BLUEPRINT & CONTEXT
**Project Name:** Proxi (The Headless Operator for Google Cloud)
**Version:** v2.1.0-GHOST
**Target:** Google Gemini 3 Hackathon (Top Prize)

## 1. THE MISSION
To build an agentic, voice-first interface that allows developers to perform "Headless SDLC" tasks (Triage, Ops, Architecture) without looking at a screen. It acts as a verifiable remote control for Google Cloud, GitHub, and Windows Servers.

## 2. THE TECH STACK
*   **AI Model (The Split Brain):** 
    *   **Voice/Relay:** Gemini 2.5 Flash Native Audio (Frontend). Handles WebRTC I/O.
    *   **Core Reasoning:** Gemini 3 Pro (Backend). Handles the "Hive Mind" orchestration with **Thinking** enabled.
    *   **Verifier:** Gemini 3 Pro (Backend). Acts as a hostile QA auditor.
    *   **Vision:** Gemini 3 Pro Vision (Backend). Used for high-speed screenshot analysis (`gemini-3-pro-image-preview`).
*   **Backend:** Python 3.12+ with **FastAPI** using the `google-genai` SDK.
*   **Streaming Protocol:** NDJSON (Newline Delimited JSON) for real-time thought streaming.
*   **Simulation Strategy:** Factory Pattern (`MockDesktopService` vs `RealDesktopService`) for safe demos.
*   **Orchestration:** **Triple Handshake Protocol** (Assign -> Execute -> Verify).
*   **Frontend (Simulator):** React + Tailwind CSS + Vite.
*   **Infrastructure:** Google Cloud Run (Dockerized) OR Windows Server (Bare Metal).

## 3. FEATURE MAPPING (Previous vs Current)

| Feature | Previous Name | Current Implementation |
| :--- | :--- | :--- |
| **Hierarchical Agents** | "The Hive" | **Executive Relay Pattern**. Frontend (Secretary) delegates to Backend (Executive). |
| **Desktop Control** | "Motor Cortex" | **Ghost Service (`desktop/real.py`)**. Toggled via `RUNTIME_MODE=REAL`. |
| **RAG / Knowledge** | "Knowledge Base" | **Standard Tools**. `query_knowledge_base` is available to the backend model. |
| **Verification** | N/A (New) | **The Truth Layer**. `orchestrator.py` independently audits task completion. |

## 4. ARCHITECTURE OVERVIEW

### The Executive Relay Pattern
Proxi uses a **Relay Architecture** to maximize the strengths of different Gemini models.
1.  **The Ear (Gemini 2.5):** Sits in the Frontend. It listens to the user via WebRTC. It has **zero** logic tools. It delegates intent via `delegate_task`.
2.  **The Hive Mind (Gemini 3 Pro):** The Backend receives the intent.
    *   **Phase 1 (Planner):** Consults Knowledge Base, creates a Mission with **Verification Criteria**.
    *   **Phase 2 (Executor):** Executes tools (Shell, GCP, GitHub, Desktop).
    *   **Phase 3 (Verifier):** The **Truth Layer**. Independently checks system state (CPU, HTTP, Screenshot) before marking a task complete.
3.  **The Neural Trace:** The Backend streams thoughts, tool outputs, and verification results back to the Frontend.

### The Truth Layer (Verifiable Agent)
To solve "LLM Hallucination" in Ops, Proxi never blindly trusts the agent.
1.  **Mission Assignment:** `assign_mission(goal="Fix CPU", criteria={"metric": "cpu", "threshold": 50})`
2.  **Independent Audit:** When the agent says "Done", the Orchestrator runs a hard system check (e.g., `psutil.cpu_percent()`).
3.  **Judgment:** If the metric fails, the agent is forced to retry. If it fails twice, it triggers `escalate_to_human`.

## 5. CAPABILITIES

### A. Headless Ops (Standard)
*   "Check the logs for service X."
*   "Restart the pod."
*   "List open PRs."

### B. Ghost Operator (Desktop)
*   **Hybrid Vision:** Uses `pyautogui` and `pywinauto` on Windows.
*   **Simulation Mode (Demo):** If `RUNTIME_MODE=DEMO`, loads a `MockDesktopService` that simulates CPU spikes and process lists for Hackathon Judges.

### C. Visual Verification
*   The agent can take a screenshot, send it to Gemini 3 Pro Vision, and verify UI states (e.g., "Is the error banner gone?").

## 6. SPRINT STATUS
*   ✅ **Verifiable Agent Architecture (Truth Layer)**
*   ✅ **Demo / Hackathon Judge Mode (Mock Incidents)**
*   ✅ **Hive Orchestrator (Triple Handshake)**
*   ✅ Executive Relay (Voice -> Backend -> Voice)
*   ✅ Real-time Neural Trace Visualization
*   ✅ OS-Agnostic Desktop Service (Factory Pattern)

## 7. RISK ANALYSIS & ROADMAP
*   **Latency:** The "Verify" step adds time. 
    *   *Mitigation:* Use Gemini 3 Flash for Vision checks to keep it fast.
*   **Safety:** Giving an AI mouse control is dangerous.
    *   *Mitigation:* "Atomic Mode" (Human authorization required for every click) - *Currently disabled for Demo flow.*
