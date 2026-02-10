# 06 — Security

## Security Model Overview

Proxi implements a defense-in-depth security model across four layers:

```
┌─────────────────────────────────────────────────────────┐
│  Layer 1: Architecture Isolation                         │
│  Core (brain) ≠ Agent (hands) — separate processes      │
├─────────────────────────────────────────────────────────┤
│  Layer 2: Authentication & Authorization                 │
│  Session cookies, agent API keys, role-based access      │
├─────────────────────────────────────────────────────────┤
│  Layer 3: Command Guardrails                             │
│  Blocked/approval/safe patterns, file guards, escalation │
├─────────────────────────────────────────────────────────┤
│  Layer 4: Runtime Protection                             │
│  Non-root containers, path restrictions, input locking   │
└─────────────────────────────────────────────────────────┘
```

---

## Layer 1: Architecture Isolation

### Split Architecture

The most fundamental security decision: **Proxi Core never executes desktop tools locally**.

| Component | Has Access To | Does NOT Have |
|-----------|--------------|---------------|
| **Core** | GEMINI_API_KEY, user DB, sessions, conversation history | Desktop tools, local file system ops |
| **Agent** | Local desktop, terminal, filesystem | User DB, sessions, API keys*, conversation history |
| **Frontend** | Chat UI only | Any backend secrets |

> *Agents optionally hold `GEMINI_API_KEY` for local visual grounding only.

### Blast Radius Analysis

| Scenario | Impact |
|----------|--------|
| Agent compromised | Attacker gets desktop access on that machine only. No user data, no API keys, no other agents. |
| Core compromised | Attacker gets API key and user sessions. Cannot directly execute desktop tools. |
| Frontend compromised | XSS risk only. No secrets in client bundle (except `VITE_GEMINI_API_KEY` — known gap). |

### Agent Communication Security

All Core ↔ Agent communication uses:
- **X-Agent-Key header**: Shared secret (`PROXI_AGENT_KEY` env var)
- **HTTP (not HTTPS internally)**: Acceptable within Docker network or Tailscale mesh
- **30-second timeouts**: Prevents hanging connections

```python
# Core side (proxy_adapter.py)
headers = {"X-Agent-Key": self.agent_key}
response = requests.post(f"{agent_url}/execute", json=payload, headers=headers)

# Agent side (agent_server.py)
async def verify_agent_key(x_agent_key: Optional[str] = Header(None)):
    if AGENT_API_KEY and x_agent_key != AGENT_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing agent key")
```

---

## Layer 2: Authentication & Authorization

### User Authentication (`auth_service.py`)

#### Password Authentication

- **Hashing**: bcrypt with 12 rounds
- **Legacy migration**: SHA-256 hashes (from early development) auto-upgrade to bcrypt on successful login
- **First-run**: Generates random 16-char passwords for default users (demo, judge, admin), prints to stdout and saves to `INITIAL_CREDENTIALS.txt`

```python
def _hash_password(self, password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')
```

#### Session Management

| Property | Value |
|----------|-------|
| Session ID | `secrets.token_hex(32)` (64 hex chars) |
| Default timeout | 6 hours |
| Remember-me timeout | 24 hours |
| Storage | JSON file (`auth/sessions.json`) |
| Delivery | HTTP cookie (`session_id`) |
| Refresh | Auto-refresh on validation |

Sessions are persisted to disk and survive server restarts. Expired sessions are pruned on load and during cleanup.

#### Magic Links (Passwordless Access)

Designed for hackathon judges who shouldn't need credentials:

| Property | Default |
|----------|---------|
| Token | `secrets.token_urlsafe(32)` |
| Expiry | 72 hours |
| Max uses | 10 |
| Role | `judge` |

Magic links create virtual users on first redemption. Each use decrements `uses_remaining`.

```
https://proxi.example.com/magic/[token]
  → Validates token
  → Creates session
  → Creates virtual user with assigned role
  → Sets session cookie
  → Redirects to app
```

#### Roles

| Role | Access Level |
|------|-------------|
| `user` | Chat, sessions, workstation viewing |
| `judge` | Same as user (for hackathon evaluation) |
| `admin` | All of above + magic link management, workstation CRUD, login events |

#### Login Event Tracking

Every login (password or magic link) is logged:
```json
{
  "timestamp": "2026-02-10T14:00:00",
  "username": "judge_abc",
  "role": "judge",
  "login_type": "magic_link",
  "magic_link_label": "Hackathon Judge Panel",
  "ip_address": "203.0.113.42",
  "user_agent": "Mozilla/5.0..."
}
```

Last 100 events retained, accessible via `/api/admin/login-events`.

---

## Layer 3: Command Guardrails (`command_guard.py`)

### Overview

The CommandGuard system classifies every terminal command into three risk levels before execution:

```
Command → CommandGuard.check_command_safety()
    │
    ├─ BLOCKED → "BLOCKED: {reason}" (never executes)
    ├─ NEEDS_APPROVAL → "APPROVAL_REQUIRED:{id}:{reason}" (waits for user)
    └─ SAFE → Execute immediately
```

### Risk Classification

#### BLOCKED Commands (34 patterns)

Commands that are **never allowed**, regardless of context:

| Category | Examples |
|----------|---------|
| **System destruction** | `rm -rf /`, `rm -rf /*`, `format C:`, `mkfs` |
| **Boot/firmware** | `dd if=.*/dev/sd`, `bcdedit`, `bootrec` |
| **Fork bombs** | `:(){:\|:&};:` |
| **Registry destruction** | `reg delete HKLM`, `reg delete HKCR` |
| **Credential theft** | `mimikatz`, `hashdump`, `lsass` |
| **Firewall disable** | `netsh advfirewall set.*off`, `ufw disable`, `iptables -F` |
| **Reverse shells** | `bash -i >& /dev/tcp`, `nc -e /bin/sh`, `python -c.*socket` |
| **Download & execute** | `curl\|bash`, `wget\|sh`, `iex.*webclient` |
| **Disk operations** | `dd if=`, `> /dev/sd` |
| **Privilege persistence** | `visudo`, `passwd root` |

#### NEEDS_APPROVAL Commands (30 patterns)

Commands requiring explicit user approval:

| Category | Examples |
|----------|---------|
| **Package management** | `pip install`, `npm install -g`, `apt install`, `choco install` |
| **Process killing** | `kill`, `taskkill`, `Stop-Process` |
| **Service control** | `systemctl stop/restart`, `sc stop/start`, `net stop/start` |
| **File deletion** | `rm -r`, `del /s`, `Remove-Item -Recurse` |
| **User management** | `useradd`, `usermod`, `net user` |
| **Permissions** | `chmod`, `chown`, `icacls` |
| **Scheduling** | `crontab -e`, `schtasks /create`, `at` |
| **Docker operations** | `docker rm`, `docker stop`, `docker compose down` |
| **Network config** | `iptables -A`, `netsh interface` |
| **Registry edits** | `reg add`, `Set-ItemProperty.*Registry` |
| **Environment changes** | `setx`, `[Environment]::SetEnvironmentVariable` |

#### SAFE Commands (80+ patterns)

Commands that execute without any gate:

| Category | Examples |
|----------|---------|
| **Listing** | `ls`, `dir`, `cat`, `type`, `head`, `tail`, `find`, `tree` |
| **System info** | `whoami`, `hostname`, `uname`, `systeminfo`, `Get-Process` |
| **Network info** | `ping`, `curl -I`, `nslookup`, `ipconfig`, `netstat` |
| **Git (read)** | `git status`, `git log`, `git diff`, `git branch` |
| **Docker (read)** | `docker ps`, `docker images`, `docker logs` |
| **Monitoring** | `top`, `htop`, `ps aux`, `df`, `free`, `uptime` |
| **Version checks** | `python --version`, `node --version`, `npm --version` |

### FileGuard

Separate guard for file system operations:

#### Protected Paths
```python
PROTECTED_PATHS = [
    "/etc/passwd", "/etc/shadow", "/etc/sudoers",
    "/root/.ssh", "/root/.bashrc",
    "C:\\Windows\\System32\\config",
    "C:\\Windows\\System32\\drivers",
    ".env", ".env.local", ".env.production",
    "id_rsa", "id_ed25519",
    # ... more
]
```

#### Sensitive File Extensions
```python
SENSITIVE_EXTENSIONS = [
    ".pem", ".key", ".crt", ".pfx", ".p12",
    ".env", ".secrets", ".credentials",
    ".kdbx", ".keychain",
]
```

### Privilege Escalation Detection

Patterns that indicate attempts to gain elevated privileges:

```python
PRIVILEGE_ESCALATION_PATTERNS = [
    r"sudo\s+su\b",
    r"sudo\s+-i\b",
    r"runas\s+/user:administrator",
    r"setcap\b",
    r"setuid\b",
    # ...
]
```

### Full Security Check

`full_security_check(command)` combines all three guards:

```python
def full_security_check(command: str) -> dict:
    return {
        "command_check": check_command_safety(command),
        "file_check": check_file_safety(command),
        "privilege_escalation": detect_privilege_escalation(command),
        "overall_risk": max_risk_level,
        "all_reasons": combined_reasons
    }
```

### Approval Flow

1. Tool wrapper calls `check_command_safety(command)`
2. If `NEEDS_APPROVAL`: generates `approval_id` (16-byte URL-safe token), stores in `pending_approvals` dict
3. Returns `APPROVAL_REQUIRED:{approval_id}:{reason}` to LLM
4. LLM output intercepted by SSE handler → `approval_request` event to frontend
5. Frontend shows modal with command, reason, 5-minute countdown
6. User clicks Approve → `POST /api/approve/{approval_id}`
7. `approve_command()` retrieves stored command, executes it, caches hash for session auto-approval
8. User clicks Deny → `POST /api/deny/{approval_id}` → command discarded

**Session auto-approval**: Once a command is approved, its SHA-256 hash is stored per-session. If the same command appears again in the same session, it auto-approves.

**DEV mode**: When `PROXI_DEV_MODE=true`, `NEEDS_APPROVAL` commands are auto-approved (never for `BLOCKED`).

**Expiry**: Pending approvals expire after 5 minutes.

---

## Layer 4: Runtime Protection

### Container Security

Both Dockerfiles implement non-root execution:

```dockerfile
# Core (Dockerfile)
RUN groupadd -r proxi && useradd -r -g proxi proxi
RUN chown -R proxi:proxi /app
# Uses gosu in entrypoint to switch from root → proxi

# Agent (Dockerfile.agent)
RUN groupadd -r proxi && useradd -r -g proxi proxi
USER proxi
```

### Agent File Upload Restriction

File uploads to agents are restricted to home directory or `/tmp`:

```python
home = os.path.expanduser("~")
if not file_path.startswith(home) and not file_path.startswith("/tmp"):
    return {"success": False, "error": "Can only write to home directory or /tmp"}
```

### Agent File Download Limit

Downloads capped at 50MB to prevent memory exhaustion:

```python
if file_size > 50 * 1024 * 1024:
    return {"success": False, error: "File too large (max 50MB)"}
```

### Input Thread Safety

`RealDesktopService` uses a `threading.Lock` for all mouse/keyboard operations to prevent race conditions from concurrent tool calls:

```python
with self._input_lock:
    pyautogui.moveTo(x, y, duration=0.1)
    pyautogui.click()
```

### Agent-Level Command Blocking

In addition to Core's CommandGuard, agents have their own local blocklist (`real.py`):

```python
BLOCKED_PATHS = ['/etc/shadow', '/etc/gshadow', '/etc/sudoers', ...]
BLOCKED_PATTERNS = ['rm -rf /', 'chmod 777', 'curl|bash', ':(){:|:&};:', ...]
```

This provides defense-in-depth: even if Core's guard is bypassed, the agent has its own safety layer.

### PyAutoGUI Failsafe

```python
pyautogui.FAILSAFE = True   # Move mouse to corner to abort
pyautogui.PAUSE = 0.1       # 100ms pause between actions
```

---

## Known Security Gaps

| Gap | Risk | Mitigation Status |
|-----|------|-------------------|
| `VITE_GEMINI_API_KEY` in frontend bundle | API key exposure in client JS | Known risk; planned to proxy all API calls through Core |
| No RBAC enforcement beyond role field | Admin/judge/user roles exist but granular permissions not enforced | Post-hackathon enhancement |
| No per-agent permissions | Any authenticated user can control any agent | Planned: agent-level ACLs |
| No audit logging | Tool executions not persistently logged with user attribution | Planned: audit trail table |
| HTTP between Core and Agent | Traffic readable on network | Acceptable within Docker/Tailscale; TLS planned for production |
| Session cookies without Secure flag | Could be intercepted on HTTP | Set `Secure=True` when behind HTTPS reverse proxy |
| No rate limiting on API | Potential for abuse | Planned: Cloudflare/nginx rate limiting |
| No 2FA for Windows agents | Single-factor agent key only | Post-hackathon: mutual TLS or certificate auth |

---

## Security Configuration

### Environment Variables

| Variable | Purpose | Required By |
|----------|---------|-------------|
| `GEMINI_API_KEY` | Google Gemini API access | Core (required), Agent (optional) |
| `PROXI_AGENT_KEY` | Core ↔ Agent authentication | Core + Agent (recommended) |
| `PROXI_DEV_MODE` | Auto-approve sensitive commands | Core (dev only, never production) |
| `GITHUB_TOKEN` | GitHub integration | Core (optional) |

### CORS Configuration

```python
allow_origins = [
    "http://localhost:4002",
    "http://localhost:5173",
    "https://proxi.yourdomain.com",
    # Configurable via CORS_ORIGINS env var
]
```

---

*Previous: [Tools Reference ←](05_tools_reference.md) | Next: [Prompt Engineering →](07_prompt_engineering.md)*
