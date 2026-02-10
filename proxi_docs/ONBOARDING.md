# Proxi — Onboarding Guide

**For new developers and LLM coding assistants starting a fresh session.**

> Read this document first. It tells you what Proxi is, where everything lives, what's done, what's planned, and which docs to read next.

---

## 1. What is Proxi?

Proxi is a **headless OS-level AI agent** that executes real work on real computers — controlled from your phone. It's built for the Google Gemini Hackathon (judging Feb 10-27, 2026).

**Core idea:** You send a natural language command from your phone → Proxi controls a Windows/Linux desktop (apps, terminals, browsers, legacy systems) → proves completion with screenshots → pauses for approval on sensitive actions.

**Live site:** [proxi.audista.com](https://proxi.audista.com)

---

## 2. Architecture (30-second version)

```
Phone (React UI, port 4002)
  → Proxi Core (FastAPI, port 4000) — holds API keys, auth, LLM orchestration
    → Agents (port 4001/8081) — isolated tool execution, no secrets
```

- **Core** talks to Gemini 3 Flash/Pro, manages sessions, routes tool calls to the active agent
- **Agents** implement `/health`, `/execute`, `/capabilities`, `/ground`
- **Security split:** If an agent is compromised, Core (with keys + user DB) is safe
- **Agent auth:** `X-Agent-Key` header with shared `PROXI_AGENT_KEY`

---

## 3. Repository Structure

```
proxi-ai/                    ← PUBLIC repo (hackathon submission)
├── backend/                 ← Python FastAPI backend
│   ├── main.py              ← Core API endpoints (~990 lines)
│   ├── agent_server.py      ← Agent API endpoints (~680 lines)
│   ├── database.py          ← SQLite schema + CRUD
│   ├── services/
│   │   ├── gemini_service.py    ← AI orchestration, tools (~1930 lines, the big file)
│   │   ├── orchestrator.py      ← Mission tracking, Triple Handshake
│   │   └── desktop/             ← Factory pattern: proxy, real, null, mock, linux
│   ├── tools/
│   │   └── command_guard.py     ← Blocked/approval command patterns
│   ├── auth/
│   │   └── auth_service.py      ← Login, sessions, magic links, bcrypt
│   └── config/
│       ├── modes.json           ← Execution modes (quick/balanced/thorough)
│       └── prompts/             ← Modular prompt sections
├── frontend/                ← React 18 + TypeScript + Vite + Tailwind
│   ├── App.tsx              ← Main app entry
│   ├── components/          ← 26 React components
│   └── hooks/               ← Custom hooks (auth, health, Gemini Live, etc.)
├── proxi_docs/              ← Comprehensive documentation (READ THESE)
├── demo-apps/               ← Functional Electron demo apps (CRM, Pricing)
├── scripts/                 ← Deployment and setup scripts
├── soc-forensics/           ← SOC forensic investigation simulation
├── docker compose.yml       ← 3-container deployment
├── DEPLOYMENT.md            ← Detailed production deployment guide
├── USER_GUIDE.md            ← End-user instructions
└── CHANGELOG.md             ← Version history
```

---

## 4. Key Technical Decisions

| Decision | Rationale |
|----------|-----------|
| **Gemini 3 Flash for most tasks** | Fast, cheap, good enough. Pro only for "thorough" mode. |
| **Session cookies (not JWT)** | Simpler for hackathon. Cookie-based auth with httpOnly. |
| **SQLite (not Postgres)** | Single-server deployment, no need for multi-node DB. |
| **Global `_active_agent_url`** | Known limitation — means one active agent per server, not per user. Fix planned (B2). |
| **Windows agent holds GEMINI_API_KEY** | Deliberate — local visual grounding is 10x faster than round-trip to Core. |
| **`NullDesktopService` as default** | Safety net — if no agent selected, all desktop tools return error instead of executing locally on Core. |

---

## 5. What's Done (Public Repo)

All Part A fixes from the action plan are implemented:

- ✅ **A1:** Session ownership checks on all 9 session endpoints
- ✅ **A3:** Agent `/capabilities` requires auth
- ✅ **A4:** Agent demo endpoints require auth
- ✅ **A5:** Evidence persistence moved from in-memory dict to SQLite
- ✅ **A6:** ThreadPoolExecutor reuse in ProxyDesktopService
- ✅ **A8:** Approval expiry cleanup (auto-sweep on access)
- ✅ **A9:** Log rotation (10MB, 3 backups)
- ✅ **Cleanup:** Old docs/, demo/ HTML, .bat files removed
- ✅ **README:** Rewritten to align with landing page messaging

**A2 (magic link admin auth standardization)** moved to Part B — judges are actively using magic links during hackathon judging, cannot risk breaking the flow.

**A7 (`verify: "auto"` in modes.json)** — confirmed as dead code. `verify_mode` is assigned but never referenced; verification happens via prompt modules, not config flag.

---

## 6. What's Planned (New Private Repo)

See [`proxi_docs/ACTION_PLAN.md`](./ACTION_PLAN.md) Part B for the full list. Highlights:

| Priority | Feature | Why |
|----------|---------|-----|
| 🔴 High | **B1: RBAC middleware** | Per-endpoint role enforcement |
| 🔴 High | **B2: Per-session agent routing** | Fix global `_active_agent_url` — multi-user safety |
| 🟡 Med | **B3: Escalate-to-Human UI** | Backend emits events, frontend doesn't render them |
| 🟡 Med | **B4: Real Slack/Linear** | Replace mock integrations with actual API calls |
| 🟡 Med | **B5: Knowledge base / RAG** | Replace mock `query_knowledge_base()` with ChromaDB |
| 🟡 Med | **B6: Backend voice relay** | Eliminate `VITE_GEMINI_API_KEY` exposure in frontend |
| 🟡 Med | **A2: Magic link auth cleanup** | Standardize admin auth checks (post-judging) |

---

## 7. Which Docs to Read (Priority Order)

For a **new developer** joining the project:

1. **This file** — you're here
2. [`proxi_docs/01_overview.md`](./01_overview.md) — tech stack, value prop
3. [`proxi_docs/02_architecture.md`](./02_architecture.md) — security split, component flow
4. [`proxi_docs/04_agent_system.md`](./04_agent_system.md) — how agents work, the /execute contract
5. [`proxi_docs/ACTION_PLAN.md`](./ACTION_PLAN.md) — what's been fixed, what's next

For a **fresh LLM coding session** (Cascade, Cursor, etc.):

1. **This file** — establishes context
2. [`proxi_docs/ACTION_PLAN.md`](./ACTION_PLAN.md) — current status and next tasks
3. Relevant module docs as needed (03-11)

For **deployment/ops:**

1. [`proxi_docs/09_deployment.md`](./09_deployment.md) — environments, Docker, agents
2. Root [`DEPLOYMENT.md`](../DEPLOYMENT.md) — detailed production guide

---

## 8. Development Environment

| Environment | OS | Purpose |
|-------------|-----|---------|
| **Dev repo** | Windows 11 | `E:\data\proxi-ai` — coding, testing |
| **Windows Agent** | Windows 11 | `E:\data\proxi-win-agent` — separate clone, runs natively |
| **Production** | Ubuntu Linux (Oracle Cloud) | Docker Compose: frontend + Core + Linux Agent |

**Key env vars:** `GEMINI_API_KEY`, `PROXI_AGENT_KEY`, `VITE_GEMINI_API_KEY` (frontend voice), `PROXI_DEV_MODE` (NEVER in production)

**Ports:** Frontend=4002, Core=4000, Linux Agent=4001 (host) / 8081 (container), Windows Agent=8081

---

## 9. Two-Repo Strategy

| Repo | Visibility | Purpose |
|------|-----------|---------|
| `proxi-ai` (this) | **Public** | Hackathon submission. Frozen feature set. Bug fixes only. |
| `proxi-private` (new) | **Private** | Post-hackathon development. New features from Part B. |

**Workflow:**
1. Bug fixes and security patches → `proxi-ai` (public)
2. New features (B1-B12) → `proxi-private` (private)
3. Once judging completes → merge back or replace

---

*Last updated: Feb 10, 2026*
