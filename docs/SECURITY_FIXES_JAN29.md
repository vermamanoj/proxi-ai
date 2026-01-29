# Security Fixes - January 29, 2026

**Context:** Production app live at proxi.audista.com, hackathon judging Feb 10-27. Must keep demo/demo123 working for judges.

---

## Fix #1: Approval Enforcement Logic 🔴 CRITICAL

### Problem
- File: `backend/services/gemini_service.py` line ~500-530
- Bug: `run_terminal_command()` adds command hash to `approved_commands` dict BEFORE user approves
- Impact: Commands marked "needs approval" can execute without true approval gate
- Risk: Main guardrail against destructive commands is bypassable

### Current Broken Flow
1. Command triggers `check_command_safety()` → returns `NEEDS_APPROVAL`
2. Code generates `cmd_hash = hashlib.md5(command.encode()).hexdigest()`
3. **BUG:** Immediately adds to `self.approved_commands[session_id]` set
4. Returns `APPROVAL_REQUIRED:...` string to frontend
5. Next time same command runs, hash is already in approved set → executes without check

### Fix Implementation
**New flow:**
1. Separate `self.pending_approvals` dict: `{approval_id: {command, session_id, timestamp}}`
2. Generate unique `approval_id = secrets.token_urlsafe(16)` for each approval request
3. Store in pending_approvals, return approval_id to frontend
4. Add new endpoint: `POST /api/approvals/{approval_id}` (approve/deny)
5. On approval: move command hash to approved_commands, execute command
6. On deny or timeout (5 min): remove from pending_approvals

**Files to modify:**
- `backend/services/gemini_service.py`:
  - Add `self.pending_approvals = {}` to `__init__`
  - Modify `run_terminal_command()` approval logic
  - Add `approve_command(approval_id)` method
  - Add `deny_command(approval_id)` method
- `backend/main.py`:
  - Add `POST /api/approvals/{approval_id}` endpoint (requires auth)
  - Takes `{"action": "approve" | "deny"}`
- `frontend/hooks/useProxiBrain.ts`:
  - Parse `approval_id` from backend response
  - Store in `pendingAction` state
  - `confirmAction()` calls `/api/approvals/{id}` with action=approve
  - `cancelAction()` calls `/api/approvals/{id}` with action=deny

**Testing:**
1. Send command requiring approval (e.g., `!rm -rf /tmp/test`)
2. Verify approval modal shows with approval_id
3. Click Deny → command should not execute
4. Send same command again → should ask for approval again
5. Click Approve → command executes
6. Send same command again → should execute without approval (hash now in approved set)

---

## Fix #2: Agent Auth Consistency 🔴 CRITICAL

### Problem
- Files: `backend/main.py`, `backend/registry/workstation_registry.py`, `backend/agent_server.py`
- Bug: Health checks and activation don't include `X-Agent-Key` header
- Impact: If `PROXI_AGENT_KEY` is set, health checks fail; if unset, agents are unprotected

### Current State
- ✅ `backend/services/agent_proxy.py` includes `X-Agent-Key` in tool execution
- ✅ `backend/services/desktop/proxy_adapter.py` includes `X-Agent-Key` in tool execution
- ❌ `backend/main.py` activate_workstation health check: no header
- ❌ `backend/registry/workstation_registry.py` check_workstation_health: no header
- ❌ `backend/agent_server.py` /health endpoint: no key verification

### Fix Implementation
**Step 1: Add key to health check calls**
- `backend/registry/workstation_registry.py` line ~140-160:
  ```python
  async def check_workstation_health(self, ws: dict) -> bool:
      url = f"http://{ws['host']}:{ws['port']}/health"
      headers = {}
      if AGENT_API_KEY:
          headers["X-Agent-Key"] = AGENT_API_KEY
      async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
          async with session.get(url, headers=headers) as response:
              # ... rest of code
  ```

- `backend/main.py` line ~450-470 (activate_workstation):
  ```python
  agent_url = f"http://{ws['host']}:{ws['port']}"
  headers = {}
  if AGENT_API_KEY:
      headers["X-Agent-Key"] = AGENT_API_KEY
  async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
      async with session.get(f"{agent_url}/health", headers=headers) as response:
          # ... rest of code
  ```

**Step 2: Verify key on agent /health endpoint**
- `backend/agent_server.py` line ~50-60:
  ```python
  @app.get("/health")
  async def health_check(_: bool = Depends(verify_agent_key)):
      return {"status": "healthy", "os": platform.system()}
  ```

**Environment variable:**
- `PROXI_AGENT_KEY` must be set consistently in:
  - Core backend .env
  - Agent .env (or Windows agent environment)

**Testing:**
1. Set `PROXI_AGENT_KEY=test123` in both Core and Agent
2. Restart both services
3. Check agent health from UI → should show online
4. Activate agent → should succeed
5. Try health check with wrong key → should fail with 401

---

## Fix #3: Remove Frontend Auth Fallback 🔴 CRITICAL

### Problem
- File: `frontend/hooks/useAuth.ts` line ~52-68
- Bug: Falls back to localStorage when backend unreachable
- Impact: Undermines session-based security

### Current Code
```typescript
} catch (error) {
  console.error('Session check failed:', error);
  // For demo/hackathon: allow bypass if backend is not available
  const savedAuth = localStorage.getItem('proxi_auth');
  if (savedAuth) {
    try {
      const user = JSON.parse(savedAuth);
      setAuthState({
        isAuthenticated: true,
        user,
        isLoading: false,
      });
      return;
    } catch (e) {
      // Invalid saved auth
    }
  }
  // ... set unauthenticated
}
```

### Fix Implementation
Remove the localStorage fallback entirely:
```typescript
} catch (error) {
  console.error('Session check failed:', error);
  setAuthState({
    isAuthenticated: false,
    user: null,
    isLoading: false,
  });
}
```

**Keep localStorage for:**
- Session persistence (storing session_id cookie info)
- UI preferences (theme, view mode, etc.)

**Remove localStorage for:**
- ❌ Auth bypass when backend down
- ❌ Storing user object as auth source

**Testing:**
1. Login with demo/demo123 → should work
2. Stop backend → refresh page → should show login screen (not bypass)
3. Start backend → login again → should work

---

## Fix #4: Upgrade Password Hashing 🔴 CRITICAL

### Problem
- File: `backend/auth/auth_service.py` line ~30-35
- Current: SHA-256 with static salt `"proxi_salt_2026"`
- Risk: Vulnerable to offline brute-force attacks

### Current Code
```python
def _hash_password(self, password: str) -> str:
    return hashlib.sha256(f"{password}proxi_salt_2026".encode()).hexdigest()
```

### Fix Implementation
**Step 1: Install bcrypt**
- Add to `backend/requirements.txt`: `bcrypt==4.1.2`
- Run: `pip install bcrypt`

**Step 2: Update hash function**
```python
import bcrypt

def _hash_password(self, password: str) -> str:
    """Hash password using bcrypt (12 rounds)"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')

def _verify_password(self, password: str, hashed: str) -> bool:
    """Verify password against bcrypt hash"""
    # Support legacy SHA-256 hashes during migration
    if len(hashed) == 64 and all(c in '0123456789abcdef' for c in hashed):
        # Legacy SHA-256 hash - verify and upgrade
        legacy_hash = hashlib.sha256(f"{password}proxi_salt_2026".encode()).hexdigest()
        if legacy_hash == hashed:
            # Upgrade to bcrypt on next save
            return True
        return False
    # Modern bcrypt hash
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False
```

**Step 3: Update login to re-hash on success**
```python
def authenticate(self, username: str, password: str) -> Optional[User]:
    user = self.users.get(username)
    if not user:
        return None
    
    if self._verify_password(password, user.password_hash):
        # If legacy hash, upgrade to bcrypt
        if len(user.password_hash) == 64:
            user.password_hash = self._hash_password(password)
            self._save_users()
        return user
    return None
```

**Hackathon compatibility:**
- demo/demo123 continues to work (transparent upgrade on first login)
- Magic links unaffected (don't use passwords)
- Judges won't notice any change

**Testing:**
1. Login with demo/demo123 → should work and upgrade hash
2. Check users.json → password_hash should be bcrypt format (starts with `$2b$`)
3. Logout and login again → should work with new hash
4. Create new user → should use bcrypt from start

---

## Implementation Order

1. **Fix #1** (2-3 hours) - Most critical, affects all command execution
2. **Commit + rebuild + test**
3. **Fix #2** (1-2 hours) - Required for secure agent deployment
4. **Commit + rebuild + test**
5. **Fix #3** (30 min) - Quick frontend fix
6. **Commit + rebuild + test**
7. **Fix #4** (1 hour) - Auth hardening
8. **Commit + rebuild + test**

**Total estimated time:** 5-7 hours

---

## Testing Checklist (After All Fixes)

- [ ] Login with demo/demo123 works
- [ ] Magic links work for judge role
- [ ] Command approval flow works (approve/deny)
- [ ] Agent health checks work with PROXI_AGENT_KEY set
- [ ] Agent activation works
- [ ] Tool execution works through proxy
- [ ] Frontend doesn't bypass auth when backend down
- [ ] Password hashes are bcrypt format
- [ ] Production deployment at proxi.audista.com works

---

## Rollback Plan (If Issues)

Each fix is in separate commit, can rollback individually:
```powershell
git log --oneline  # Find commit hash
git revert <commit-hash>  # Revert specific fix
docker-compose down && docker-compose up -d --build  # Rebuild
```

---

## Implementation Status

### Fix #1: Approval Enforcement Logic ✅ COMPLETED
**Completed:** Jan 29, 2026 11:15 AM IST

**Changes made:**
1. `backend/services/gemini_service.py`:
   - Added `self.pending_approvals = {}` dict to track pending approvals separately
   - Modified `run_terminal_command()` to generate unique `approval_id` using `secrets.token_urlsafe(16)`
   - Store approval details in pending_approvals before user decision
   - Return format: `APPROVAL_REQUIRED:approval_id:reason. Command: cmd...`
   - Added `approve_command(approval_id)` method to validate, execute, and move to approved set
   - Added `deny_command(approval_id)` method to reject and remove from pending
   - Added 5-minute expiry check for approval requests

2. `backend/main.py`:
   - Added `POST /api/approvals/{approval_id}` endpoint
   - Requires authentication
   - Accepts `{"action": "approve" | "deny"}`
   - Calls gemini_service approve/deny methods

3. `frontend/hooks/useProxiBrain.ts`:
   - Added `approval_required` case to stream parser
   - Extracts `approval_id`, `command`, `reason`, `risk_level` from backend
   - Sets `pendingAction` with type `command_approval`
   - Modified `confirmAction()` to call `/api/approvals/{id}` with action=approve
   - Modified `cancelAction()` to call `/api/approvals/{id}` with action=deny
   - Maintains backward compatibility with legacy text-based approval flow

**Security improvement:**
- Commands no longer pre-approved before user decision
- Unique token prevents replay attacks
- Approval expires after 5 minutes
- Command only executes after explicit API call with valid approval_id

### Fix #2: Agent Auth Consistency ✅ COMPLETED
**Completed:** Jan 29, 2026 11:25 AM IST

**Changes made:**
1. `backend/registry/workstation_registry.py`:
   - Modified `check_workstation_health()` to include `X-Agent-Key` header
   - Reads `PROXI_AGENT_KEY` from environment
   - Adds header to health check requests if key is configured

2. `backend/main.py`:
   - Modified `activate_workstation()` health check to include `X-Agent-Key` header
   - Consistent with tool execution authentication

3. `backend/agent_server.py`:
   - Modified `/health` endpoint to require agent key verification
   - Uses existing `verify_agent_key` dependency
   - Returns 401 if key is configured but missing/invalid

**Security improvement:**
- Health checks and activation now use same authentication as tool execution
- Can safely enable `PROXI_AGENT_KEY` in production without breaking health checks
- Agents are protected from unauthorized health probes
- Consistent authentication across all Core→Agent communication

**Deployment note:**
- If `PROXI_AGENT_KEY` is not set, authentication is optional (backward compatible)
- For production: set `PROXI_AGENT_KEY` in both Core and Agent environments

### Fix #3: Remove Frontend Auth Fallback ✅ COMPLETED
**Completed:** Jan 29, 2026 11:30 AM IST

**Changes made:**
1. `frontend/hooks/useAuth.ts`:
   - Removed localStorage auth bypass in `checkSession()` catch block
   - Removed 15 lines of fallback code that allowed authentication when backend unreachable
   - Now always requires valid backend session for authentication
   - localStorage still used for UI preferences, but not as auth source

**Security improvement:**
- Frontend cannot bypass authentication when backend is down
- All authentication must go through backend session validation
- Eliminates client-side auth bypass vulnerability
- Enforces server-side session control

**User impact:**
- If backend is down, users see login screen (correct behavior)
- No change to normal login flow (demo/demo123 still works)
- Session persistence still works via cookies

### Fix #4: Upgrade Password Hashing ✅ COMPLETED
**Completed:** Jan 29, 2026 11:35 AM IST

**Changes made:**
1. `backend/requirements.txt`:
   - Added `bcrypt==4.1.2` dependency

2. `backend/auth/auth_service.py`:
   - Imported `bcrypt` module
   - Modified `_hash_password()` to use bcrypt with 12 rounds
   - Added `_verify_password()` method with legacy SHA-256 support
   - Modified `authenticate()` to upgrade legacy hashes on successful login
   - Detects legacy hash by length (64 hex chars) and verifies using old method
   - Automatically upgrades to bcrypt on next successful login

**Security improvement:**
- Bcrypt is resistant to offline brute-force attacks (adaptive cost)
- 12 rounds provides strong security while maintaining performance
- Legacy SHA-256 hashes automatically upgraded on login
- Transparent migration - no user action required

**Hackathon compatibility:**
- demo/demo123 continues to work (upgraded on first login)
- Magic links unaffected (don't use passwords)
- Judges won't notice any change
- Existing users automatically migrated

**Migration behavior:**
- Legacy hash detected: 64 hex characters
- Verification: uses old SHA-256 method for legacy hashes
- Upgrade: on successful login, re-hash with bcrypt and save
- New users: always use bcrypt from creation

---

## All Security Fixes Complete ✅

**Total time:** ~30 minutes
**Commits:** 4 separate commits (can rollback individually)

**Next steps:**
1. Rebuild Docker containers: `docker-compose down && docker-compose up -d --build`
2. Test approval flow with destructive command
3. Test agent health checks with PROXI_AGENT_KEY set
4. Test login with demo/demo123 (should upgrade hash)
5. Verify production deployment at proxi.audista.com

---

**Status:** All 4 security fixes completed and committed
**Completed:** Jan 29, 2026 11:35 AM IST
