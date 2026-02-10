# 11 — Additional Context

This document captures important project context not covered in the core technical docs — frontend versions, demo scenarios, mobile strategy, security history, and infrastructure details gleaned from the project's evolution.

---

## 1. AI Model Usage

Proxi uses multiple Gemini model generations for different purposes:

| Purpose | Model | Location | Notes |
|---------|-------|----------|-------|
| **Fast Reasoning** | `gemini-3-flash-preview` | Core (GeminiService) | Quick/balanced modes, tool execution |
| **Deep Reasoning** | `gemini-3-pro-preview` | Core (GeminiService) | Thorough mode, complex multi-step tasks |
| **Vision Analysis** | `gemini-3-flash-preview` | Core (GeminiService) | Screenshot analysis, UI element identification |
| **Image Generation** | `gemini-3-pro-image-preview` | Core (GeminiService) | Image creation tasks |
| **Visual Grounding** | `gemini-3-flash-preview` | Agent (`/ground` endpoint) | Local element finding on Windows agent |
| **Voice I/O** | Gemini 2.5 Live Native Audio | Frontend (WebRTC) | Real-time voice via `useGeminiLive.ts` |

> **Key distinction:** LLM orchestration uses Gemini 3 (Flash/Pro). Voice uses Gemini 2.5 Live for native audio streaming via WebRTC in the frontend — this is a separate API from the text/tool calling API.

---

## 2. Frontend Versions

The frontend has evolved through three versions. As of v3.5.0:

| Route | Component | Status | Description |
|-------|-----------|--------|-------------|
| `/` (default) | `AppV3` | **Primary** | Sidebar layout (ChatGPT/Gemini style), lazy voice loading, optimized for demo |
| `/#/v2` | `App` | Legacy | Admin console, magic links, session history — still functional |
| `/#/v1` | `AppV2` | Deprecated | Temporary layout from early development |

**Key v3 changes:**
- Lazy voice connection (click mic to connect → faster page load)
- Sidebar layout with session list
- Streamlined UI with fewer components
- Mobile-first responsive design

---

## 3. Demo Scenarios

### 3.1 Sales Emergency Demo (Primary)

The flagship demo scenario for the hackathon:

> *"Sarah is closing a $2.3M deal. Competition just undercut by 12%. She has 10 minutes to respond but can't leave the meeting room. She pulls out her phone..."*

**Demo flow:**
1. Voice: "Check our pricing system for minimum margin" → Vision analysis of legacy CRM
2. Voice: "What's Acme Corp's history in our CRM?" → Multi-app navigation
3. Voice: "Find the brand template PPT I downloaded" → File discovery
4. Voice: "Create a business case slide" → PowerPoint automation

**Demo apps** (in `demo-apps/`):
- **Pricing App** (`demo-apps/pricing-app/`) — Electron app with JSON backend, multi-tab UI
- **CRM App** (`demo-apps/crm-app/`) — Electron app with customer records, deal pipeline

### 3.2 SOC Forensic Investigation Demo

A realistic cybersecurity incident simulation (`soc-forensics/`):

- **Scenario**: Production server with 100% CPU from crypto-miner
- **Attack vector**: Next.js Server Action RCE (CVE-2024-46982)
- **Red herrings**: SSH brute force (clean logs), database exploit (firewall blocks it)
- **Real root cause**: Web app RCE → XMRig miner download → systemd persistence

**Multi-desktop investigation flow:**
1. Linux Container → triage (top, ps, netstat)
2. Switch to Windows → verify OCI firewall rules in cloud console
3. Back to Linux → find RCE evidence in application logs
4. Map persistence mechanisms, generate attack path diagram

**Container**: `proxi-forensics:v2` with built-in Proxi agent server on port 5081

### 3.3 Demo Mode (`PROXI_DEV_MODE`)

When `PROXI_DEV_MODE=true` in `.env`:
- Command Guard auto-approves `NEEDS_APPROVAL` commands
- Allows `BLOCKED` commands with warning log (for demo recordings)
- **Never enable in production**

---

## 4. Mobile Strategy

### PWA (Primary — Production)

Progressive Web App support added in v3.4.0:
- `frontend/public/manifest.json` — App metadata, icons
- `frontend/public/sw.js` — Service worker for offline caching
- Install: Visit HTTPS URL → "Add to Home Screen" → standalone mode

### Capacitor (Alternative — Android)

Native wrapper for Android using Capacitor 5.x:
- `frontend/capacitor.config.ts` — Configuration
- `frontend/android/` — Generated Android project
- Known issues: CORS in native WebView, `VITE_GEMINI_API_KEY` exposed in APK

### Known Mobile Risk

`VITE_GEMINI_API_KEY` is bundled into the frontend (both web and APK) for Gemini Live voice. This is extractable. Planned mitigation: backend voice relay endpoint (`/api/voice/relay`) to proxy audio through Core, eliminating client-side API key need.

---

## 5. Security Fix History

All four critical security fixes from January 29, 2026 have been completed and deployed:

| Fix | Issue | Status | Impact |
|-----|-------|--------|--------|
| **#1: Approval Enforcement** | Commands pre-approved before user decision | ✅ Fixed | `pending_approvals` dict with unique `approval_id`, 5-min expiry |
| **#2: Agent Auth Consistency** | Health checks didn't include `X-Agent-Key` header | ✅ Fixed | All Core→Agent calls now include auth header |
| **#3: Frontend Auth Fallback** | localStorage bypass when backend unreachable | ✅ Fixed | Removed fallback, always requires backend session |
| **#4: Password Hashing** | SHA-256 with static salt | ✅ Fixed | Upgraded to bcrypt (12 rounds), auto-migration on login |

---

## 6. Infrastructure Stack

### Cloudflare (Production)

Production site (`proxi.audista.com`) is behind Cloudflare:
- DNS proxied through Cloudflare
- SSL termination (Full Strict mode)
- WAF managed rules enabled
- Bot protection
- Rate limiting: Login 5/min, API 30/sec

### Nginx (Reverse Proxy)

- SSE requires: `proxy_buffering off`, `proxy_cache off`
- Read timeout: 300s (for thorough mode long-running operations)
- Security headers: X-Frame-Options, X-Content-Type-Options, XSS-Protection, Referrer-Policy
- `/docs` endpoint blocked in production (returns 404)

### Tailscale (Agent Networking)

Secure mesh VPN for connecting remote Windows agents:
- WireGuard encryption, NAT-traversing
- No inbound ports needed on agent machines
- Core initiates connections TO agents (not reverse)
- ACLs restrict which devices can communicate

---

## 7. Project Evolution

### Architecture Timeline

1. **Monolith phase**: Single Windows server running UI + backend + agent as one process
2. **Split phase**: Separated into Frontend (React), Core (FastAPI), Agent (FastAPI) — 3 containers on same Windows server
3. **Multi-machine phase**: Core + Frontend on Oracle Cloud Ubuntu, Windows agent on separate machine via Tailscale
4. **Current**: Production on Ubuntu, development on Windows 11, agents can be anywhere

### Legacy Patterns (Deprecated)

| Pattern | Status | Replaced By |
|---------|--------|-------------|
| `RUNTIME_MODE=DEMO/REAL` | Deprecated | Agent mode with remote workstations |
| SHA-256 password hashing | Migrated | bcrypt (auto-upgrade on login) |
| localStorage auth fallback | Removed | Server-side sessions only |
| Frontend v1/v2 routes | Deprecated | v3 is primary (`/`) |

---

## 8. Credential Management

### First Run

On first start, Proxi auto-generates random 16-char passwords for default users:
- `demo` (role: user)
- `judge` (role: judge)
- `admin` (role: admin)

Passwords printed to stdout and saved to `backend/auth/INITIAL_CREDENTIALS.txt`. **Delete this file after noting passwords.**

### Custom Passwords

```bash
python3 scripts/set_password.py demo YourDemoPassword
python3 scripts/set_password.py admin YourAdminPassword
docker compose restart core
```

### Magic Links for Judges

Passwordless access for hackathon judges:
- Admin generates link via UI or API (`POST /api/auth/magic-link`)
- Recommended settings: role=judge, expires=408h (17 days for judging period), uses=50
- URL format: `https://proxi.audista.com?magic=<TOKEN>`

---

*Previous: [Developer Guide ←](10_developer_guide.md) | Back to: [Index ←](README.md)*
