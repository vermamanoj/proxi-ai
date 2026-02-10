# Proxi Action Plan

**Created:** Feb 10, 2026  
**Context:** Public repo (proxi-ai) is hackathon submission. New private repo for post-hackathon features.

---

## 1. API Authentication Audit

### Core Server (`backend/main.py`) — 37 endpoints

| # | Endpoint | Method | Auth | Admin | Status | Issue |
|---|----------|--------|------|-------|--------|-------|
| 1 | `/` | GET | ❌ | - | ✅ OK | Info only |
| 2 | `/api/health` | GET | ❌ | - | ✅ OK | Health check, no secrets |
| 3 | `/api/auth/login` | POST | ❌ | - | ✅ OK | This IS the auth entry point |
| 4 | `/api/auth/session` | GET | ✅ cookie | - | ✅ OK | Session validation |
| 5 | `/api/auth/logout` | POST | ✅ cookie | - | ✅ OK | |
| 6 | `/api/auth/magic-link` | POST | ✅ manual | ✅ manual | ⚠️ | Uses manual auth check instead of `require_auth(require_admin=True)` — functional but inconsistent |
| 7 | `/api/auth/magic-link/{token}` | GET | ❌ | - | ✅ OK | Validate only, no redeem |
| 8 | `/api/auth/magic-link/{token}/redeem` | POST | ❌ | - | ✅ OK | This IS a login mechanism |
| 9 | `/api/auth/magic-links` | GET | ✅ manual | ✅ manual | ⚠️ | Same inconsistency as #6 |
| 10 | `/api/auth/magic-link/{token}` | DELETE | ✅ manual | ✅ manual | ⚠️ | Same inconsistency as #6 |
| 11 | `/api/auth/login-events` | GET | ✅ manual | ✅ manual | ⚠️ | Same inconsistency as #6 |
| 12 | `/api/waitlist` | POST | ❌ | - | ✅ OK | Intentionally public |
| 13 | `/api/waitlist` | GET | ✅ require_auth | ✅ manual | ✅ OK | |
| 14 | `/api/chat` | POST | ✅ require_auth | - | ✅ OK | |
| 15 | `/api/vision` | POST | ✅ require_auth | - | ✅ OK | |
| 16 | `/api/vision-action` | POST | ✅ require_auth | - | ✅ OK | |
| 17 | `/api/approvals/{id}` | POST | ✅ require_auth | - | ✅ OK | |
| 18 | `/api/missions` | GET | ✅ require_auth | - | ✅ OK | |
| 19 | `/api/missions/{id}/items` | GET | ✅ require_auth | - | ✅ OK | |
| 20 | `/api/items/{id}/status` | POST | ✅ require_auth | - | ✅ OK | |
| 21 | `/api/desktop/execute` | POST | ✅ require_auth | - | ✅ OK | |
| 22 | `/api/sessions` | GET | ✅ require_auth | - | ✅ OK | Filtered by user_id |
| 23 | `/api/sessions` | POST | ✅ require_auth | - | ✅ OK | |
| 24 | `/api/sessions/{id}` | GET | ✅ require_auth | - | ⚠️ **ISSUE** | No ownership check — any user can read any session by ID |
| 25 | `/api/sessions/{id}` | PUT | ✅ require_auth | - | ⚠️ **ISSUE** | No ownership check — any user can modify any session |
| 26 | `/api/sessions/{id}/cancel` | POST | ✅ require_auth | - | ⚠️ **ISSUE** | No ownership check |
| 27 | `/api/sessions/{id}/messages` | POST | ✅ require_auth | - | ⚠️ **ISSUE** | No ownership check |
| 28 | `/api/sessions/{id}/goals` | POST | ✅ require_auth | - | ⚠️ **ISSUE** | No ownership check |
| 29 | `/api/sessions/{id}/goals/{gid}` | PUT | ✅ require_auth | - | ⚠️ **ISSUE** | No ownership check |
| 30 | `/api/sessions/{id}/close` | POST | ✅ require_auth | - | ⚠️ **ISSUE** | No ownership check |
| 31 | `/api/sessions/{id}/images` | POST | ✅ require_auth | - | ⚠️ **ISSUE** | No ownership check |
| 32 | `/api/sessions/{id}/images` | GET | ✅ require_auth | - | ⚠️ **ISSUE** | No ownership check |
| 33 | `/api/images/{id}` | GET | ✅ require_auth | - | ✅ OK | Flat lookup, acceptable |
| 34 | `/api/files/download` | POST | ✅ require_auth | - | ✅ OK | |
| 35 | `/api/files/upload` | POST | ✅ require_auth | - | ✅ OK | |
| 36 | `/api/workstations` | GET | ✅ require_auth | - | ✅ OK | |
| 37 | `/api/workstations/{id}` | GET | ✅ require_auth | - | ✅ OK | |
| 38 | `/api/workstations/{id}/health` | GET | ✅ require_auth | - | ✅ OK | |
| 39 | `/api/workstations` | POST | ✅ require_auth | ✅ require_admin | ✅ OK | Properly uses `require_admin=True` |
| 40 | `/api/workstations/{id}` | DELETE | ✅ require_auth | ✅ require_admin | ✅ OK | Properly uses `require_admin=True` |
| 41 | `/api/workstations/{id}/activate` | POST | ✅ require_auth | - | ✅ OK | |
| 42 | `/api/workstations/deactivate` | POST | ✅ require_auth | - | ✅ OK | |

### Agent Server (`backend/agent_server.py`) — 8 endpoints

| # | Endpoint | Method | Auth | Status | Issue |
|---|----------|--------|------|--------|-------|
| 1 | `/` | GET | ❌ | ✅ OK | Info only |
| 2 | `/health` | GET | ✅ verify_agent_key | ✅ OK | |
| 3 | `/execute` | POST | ✅ verify_agent_key | ✅ OK | |
| 4 | `/files/download` | POST | ✅ verify_agent_key | ✅ OK | |
| 5 | `/files/upload` | POST | ✅ verify_agent_key | ✅ OK | |
| 6 | `/ground` | POST | ✅ verify_agent_key | ✅ OK | |
| 7 | `/capabilities` | GET | ❌ | ⚠️ **ISSUE** | Exposes tool list without auth |
| 8 | `/demo/trigger_incident` | POST | ❌ | ⚠️ **ISSUE** | Anyone can trigger simulated incident |
| 9 | `/demo/resolve_incident` | POST | ❌ | ⚠️ **ISSUE** | Anyone can resolve simulated incident |

### Summary of Auth Issues Found

| Issue | Severity | Endpoints Affected |
|-------|----------|-------------------|
| **Session ownership not checked** | 🔴 High | 9 session endpoints (#24-32) — any authenticated user can access any session by guessing/enumerating IDs |
| **Admin endpoints use manual auth** | 🟡 Medium | 4 magic link + login-events endpoints (#6,9,10,11) — functional but inconsistent with `require_auth` pattern |
| **Agent `/capabilities` no auth** | 🟡 Medium | 1 agent endpoint (#7) — exposes tool list to unauthenticated callers |
| **Agent demo endpoints no auth** | 🟢 Low | 2 agent endpoints (#8,9) — demo-only, mock data, agents should be behind Tailscale anyway |

---

## 2. Action Plan

### Part A: Fixes to Existing Features (Current Public Repo: `proxi-ai`)

These are bugs, security gaps, and quality issues in features that already exist and should be fixed in-place.

| # | Fix | Severity | Effort | Files to Change |
|---|-----|----------|--------|----------------|
| **A1** | **Session ownership check** — Add user_id verification to all 9 session endpoints (GET/PUT/POST). Fetch session, verify `user_id` matches authenticated user (admins bypass). | 🔴 High | 30 min | `main.py` |
| ~~A2~~ | ~~Standardize admin auth~~ — **Moved to Part B**. Judges are actively using magic links during hackathon judging (Feb 10-27). Cannot risk breaking this flow. | - | - | - |
| **A3** | **Agent `/capabilities` auth** — Add `Depends(verify_agent_key)` to `/capabilities` endpoint. | 🟡 Medium | 2 min | `agent_server.py` |
| **A4** | **Agent demo endpoints auth** — Add `Depends(verify_agent_key)` to `/demo/trigger_incident` and `/demo/resolve_incident`. | 🟢 Low | 2 min | `agent_server.py` |
| **A5** | **Evidence persistence** — `self.evidence_store = {}` (in-memory) → persist to SQLite `work_items` table. Evidence lost on every restart. | 🟡 Medium | 45 min | `gemini_service.py`, `database.py` |
| **A6** | **ThreadPoolExecutor reuse** — `ProxyDesktopService._execute_sync()` creates a new executor per call. Make it a class-level instance. | 🟢 Low | 15 min | `desktop/proxy.py` |
| **A7** | **`verify: "auto"` behavior** — Verify that `modes.json` value `"auto"` is handled correctly in code (string `"auto"` is truthy in Python). If it should behave differently from `true`, add explicit handling. | 🟡 Medium | 15 min | `gemini_service.py` |
| **A8** | **Approval expiry cleanup** — `pending_approvals` dict never cleans up expired entries. Add cleanup on access or periodic sweep. | 🟢 Low | 15 min | `gemini_service.py` |
| **A9** | **Log rotation** — `proxi_debug.log` grows unbounded. Add `RotatingFileHandler` (e.g., 10MB, 3 backups). | 🟢 Low | 10 min | `main.py` or logging config |

### Part B: New Features (New Private Repo)

These are planned but unimplemented capabilities. Build in a new private repo, merge back when ready.

| # | Feature | Priority | Effort | Description |
|---|---------|----------|--------|-------------|
| **B1** | **RBAC enforcement middleware** | 🔴 High | 2-3 hr | Per-endpoint role checking via FastAPI `Depends()`. Design already exists in `SECURITY_ROADMAP.md`. Define which endpoints require which roles. |
| **B2** | **Per-session agent routing** | 🔴 High | 3-4 hr | Replace `_active_agent_url` global with per-session dict `{session_id: agent_url}`. Currently if User A switches agent, User B's requests go to wrong agent. |
| **B3** | **Escalate-to-Human UI wiring** | 🟡 Medium | 2-3 hr | Backend emits escalation events, but frontend never renders an alert/modal. Wire `EscalateToHuman.tsx` component into `AppV3`. |
| **B4** | **Real Slack/Linear integrations** | 🟡 Medium | 3-4 hr | Replace mock `send_slack_message()` and `create_linear_ticket()` with actual webhook/API calls. Need env vars for tokens. |
| **B5** | **Knowledge base / RAG** | 🟡 Medium | 1-2 days | Replace mock `query_knowledge_base()` with actual vector DB (e.g., ChromaDB) + document ingestion pipeline. |
| **B6** | **Backend voice relay** | 🟡 Medium | 4-6 hr | `POST /api/voice/relay` — proxy audio through Core to eliminate `VITE_GEMINI_API_KEY` exposure in frontend bundle. |
| **B7** | **2FA for agent connections** | 🟢 Low | 3-4 hr | Challenge-response auth when Windows agent connects. Design in `SECURITY_ROADMAP.md`. |
| **B8** | **Per-agent permissions** | 🟢 Low | 3-4 hr | Allow/deny specific tools per agent (e.g., Linux agent can't run PPT tools). |
| **B9** | **Audit logging** | 🟢 Low | 2-3 hr | Log all tool executions, auth events, admin actions to a queryable audit table. |
| **B10** | **Container hardening** | 🟢 Low | 1-2 hr | Non-root user in Dockerfiles, read-only filesystem, drop capabilities. |
| **B11** | **Frontend architecture doc** | 🟢 Low | 2 hr | Document React components, hooks, state management, SSE parsing. |
| **B12** | **Headless operation** | 🟢 Low | 1-2 days | Virtual Display Driver for running Windows agent without physical monitor. |

---

## 3. Recommended Execution Order

### Phase 1: Security fixes in public repo (today)
1. **A1** — Session ownership check (🔴 highest risk)
2. **A2** — Standardize admin auth
3. **A3** — Agent `/capabilities` auth
4. **A4** — Agent demo endpoints auth

### Phase 2: Quality fixes in public repo (this week)
5. **A5** — Evidence persistence
6. **A7** — Verify `"auto"` mode behavior
7. **A6** — ThreadPoolExecutor reuse
8. **A8** — Approval expiry cleanup
9. **A9** — Log rotation

### Phase 3: New features in private repo (post-hackathon)
10. **B1** — RBAC enforcement
11. **B2** — Per-session agent routing
12. **B3** — Escalate-to-Human UI
13. **B4-B12** — Remaining features by priority

---

*This plan reflects the split between the public hackathon repo and the planned private development repo.*
