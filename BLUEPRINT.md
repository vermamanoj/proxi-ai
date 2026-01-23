# PROXI: SYSTEM BLUEPRINT & CONTEXT
**Project Name:** Proxi (The Headless Operator for Google Cloud)
**Date:** Jan 2026
**Target:** Google Gemini 3 Hackathon (Top Prize)

## 1. THE MISSION
To build an agentic, voice-first interface that allows developers to perform "Headless SDLC" tasks (Triage, Ops, Architecture) without looking at a screen. It acts as a remote control for Google Cloud, GitHub, and remote Windows Servers.

## 2. THE TECH STACK (Strict Adherence)
*   **AI Model:** Gemini 3 Pro (via Vertex AI) + Gemini Live API (for Real-time WebRTC Audio).
*   **Backend:** Python 3.12+ with **FastAPI**.
*   **Orchestration:** LangGraph (for stateful agent loops).
*   **Database:** 
    *   *Vector:* Pinecone (for Code RAG).
    *   *Session:* In-memory / Redis (for active conversation state).
*   **Frontend (Simulator):** React + Tailwind CSS (Web-based control plane for Judges).
*   **Infrastructure:** Google Cloud Run (Dockerized) OR Windows Server (Bare Metal).
*   **Auth:** GitHub OAuth.

## 3. ARCHITECTURE OVERVIEW
[Client: Web/Mobile] <===(WebRTC Audio)===> [Backend: FastAPI/Gemini Live]
                                                  |
                                          [The Agent Brain (LangGraph)]
                                                  |
                            -----------------------------------------------------------
                            |                   |                     |               |
                     [Tool: GitHub]     [Tool: Google Cloud]  [Tool: Shell]    [Tool: GUI]
                     (PRs, Issues)      (Logs, Restart Pods)  (PowerShell)     (Click, OCR)

## 4. CODING STANDARDS
*   **Async First:** All I/O operations (DB, API calls) must be `async/await`.
*   **Type Safety:** Strict Python type hinting (`typing.List`, `pydantic.BaseModel`).
*   **Environment:** All secrets must be loaded via `os.getenv()` using `python-dotenv`.
*   **Modularity:** Keep "Tools" separate from "Agent Logic".
*   **Mocking:** Since we are in dev, ensure every Tool has a `mock_mode=True` toggle for testing without burning API credits.

## 5. FIRST SPRINT GOAL
Build the **"Echo Loop"**.
1. Set up the FastAPI server.
2. Connect to Gemini 3 Pro API.
3. Accept a text input, send to Gemini, receive text response.
4. (Bonus) Accept Audio blob, transcribe (or use Native Audio), and respond.

## 6. Architecture

graph TD
    User((User Voice)) -->|WebRTC Stream| Bridge[API Gateway / FastAPI]
    Bridge -->|Audio Stream| Gemini[Gemini 3 Pro Live API]
    
    subgraph "The Proxi Brain"
        Gemini -->|Decide Intent| Router{Router}
        Router -->|Need Info?| RAG[(Vector DB)]
        Router -->|Action?| Tools[Tool Manager]
    end
    
    subgraph "The Hands (Tools)"
        Tools -->|Review PR| GitHub[GitHub API]
        Tools -->|Check Logs| GCP[Google Cloud SDK]
        Tools -->|PowerShell| Shell[Terminal Execution]
        Tools -->|GUI/OCR| Desktop[Windows Desktop Service]
    end
    
    Tools -->|Result| Gemini
    Gemini -->|Audio Response| Bridge
    Bridge -->|Voice| User
