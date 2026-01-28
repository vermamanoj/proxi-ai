# Proxi Security Roadmap

**Last Updated:** January 28, 2026  
**Status:** Production Readiness Planning

---

## 1. Current Security Posture

### ✅ Implemented

| Layer | Feature | Status |
|-------|---------|--------|
| **Architecture** | Core/Agent split | API keys isolated in Core |
| **Authentication** | Session-based auth | 6hr timeout, HttpOnly cookies |
| **Authorization** | User roles | demo/judge/admin stored |
| **Command Safety** | Guardrails | Blocked + approval patterns |
| **Data** | SQLite WAL | Concurrent access, no corruption |
| **Network** | Cloudflare proxy | DDoS, WAF, SSL termination |
| **CORS** | Domain whitelist | Only proxi.audista.com + localhost |
| **Cookies** | Secure flag | Auto-enabled behind HTTPS proxy |
| **Rate Limiting** | Nginx + Cloudflare | Login: 5/min, API: 30/sec |
| **Headers** | Security headers | X-Frame-Options, CSP, XSS protection |
| **Docs** | /docs blocked | 404 in production nginx |

### ⚠️ Gaps to Address (Post-Hackathon)

| Risk | Current State | Remediation |
|------|---------------|-------------|
| RBAC not enforced | Roles stored but not checked | Implement middleware |
| No 2FA | Single-factor login | Add TOTP/WebAuthn |
| Agent access open | Any user can use any agent | Per-agent permissions |
| No audit logging | Actions not recorded | Add audit trail |

---

## 2. Threat Model

### 2.1 Attack Surfaces

```
┌─────────────────────────────────────────────────────────────────┐
│                     THREAT LANDSCAPE                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  EXTERNAL                           INTERNAL                    │
│  ─────────                          ─────────                   │
│  • Credential stuffing              • Prompt injection          │
│  • Session hijacking                • Tool abuse                │
│  • API abuse                        • Privilege escalation      │
│  • DDoS                             • Data exfiltration         │
│                                                                 │
│  AGENT COMPROMISE                   INFRASTRUCTURE              │
│  ────────────────                   ──────────────              │
│  • Malicious tool execution         • Exposed API keys          │
│  • Lateral movement                 • Unpatched containers      │
│  • Data theft from desktop          • Weak network config       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Risk Prioritization

| Risk | Impact | Likelihood | Priority |
|------|--------|------------|----------|
| Prompt injection → tool abuse | High | Medium | P1 |
| Session hijacking | High | Low | P2 |
| Agent compromise | Critical | Low | P1 |
| Credential leak | High | Low | P2 |
| DDoS | Medium | Medium | P3 |

---

## 3. Security Roadmap

### Phase 1: Hackathon Hardening (Before Feb 10)

| Task | Effort | Status |
|------|--------|--------|
| Enable HTTPS on production | 2hr | ✅ Done (Cloudflare) |
| Rate limiting on login | 1hr | ✅ Done (nginx + Cloudflare) |
| Secure cookie flags (HttpOnly, Secure, SameSite) | 30min | ✅ Done |
| Remove debug endpoints | 30min | ✅ Done (/docs blocked) |
| Validate CORS origins | 30min | ✅ Done |
| Security headers (X-Frame, XSS, etc.) | 30min | ✅ Done |

### Phase 2: Production Ready (Post-Hackathon)

| Task | Effort | Description |
|------|--------|-------------|
| **RBAC Enforcement** | 4hr | Check roles on protected routes |
| **2FA for Agent Connect** | 8hr | TOTP verification before activating remote agents |
| **Per-Agent Permissions** | 4hr | User → Agent access mapping |
| **Audit Logging** | 4hr | Record all tool executions |
| **API Key Rotation** | 2hr | Scheduled key refresh |

### Phase 3: Enterprise Grade

| Task | Effort | Description |
|------|--------|-------------|
| **SSO Integration** | 16hr | SAML/OIDC for enterprise |
| **Secrets Manager** | 8hr | HashiCorp Vault / AWS Secrets |
| **SOC2 Compliance** | 40hr | Audit trail, access reviews |
| **Penetration Testing** | External | Third-party security audit |

---

## 4. Implementation Details

### 4.1 Command Guardrails (Implemented)

```python
# backend/tools/command_guard.py

BLOCKED_COMMANDS = [
    r'rm\s+-rf\s+/',           # Recursive delete root
    r'format\s+[a-zA-Z]:',     # Format disk
    r'shutdown|reboot|halt',   # System control
    r':(){ :\|:& };:',         # Fork bomb
    r'reg\s+delete\s+HKLM',    # Registry delete
]

APPROVAL_REQUIRED = [
    r'pip\s+install',          # Package install
    r'Stop-Process|taskkill',  # Kill process
    r'Remove-Item|rm\s+',      # Delete file
    r'sudo\s+',                # Privilege escalation
]
```

### 4.2 RBAC Middleware (To Implement)

```python
# backend/middleware/rbac.py

ROLE_PERMISSIONS = {
    "demo": ["chat", "view_agents"],
    "judge": ["chat", "view_agents", "trigger_demo"],
    "admin": ["chat", "view_agents", "trigger_demo", "manage_users", "manage_agents"],
}

async def check_permission(user: User, action: str) -> bool:
    return action in ROLE_PERMISSIONS.get(user.role, [])
```

### 4.3 2FA for Windows Agent (To Implement)

**Scope:** Windows agents only (not Linux docker agent)

**Admin Exception:** Judges and admins can bypass 2FA via admin portal setting.

```python
# backend/auth/agent_2fa.py

class Agent2FA:
    """2FA verification for sensitive agent activation."""
    
    # Agents requiring 2FA
    PROTECTED_AGENTS = ["win-azure", "win-desktop"]
    
    # Users exempt from 2FA (set via admin portal)
    EXEMPT_USERS = set()  # Populated from DB/config
    
    def requires_2fa(self, user: User, agent_id: str) -> bool:
        """Check if 2FA is required for this user + agent combo."""
        # Admins can grant exemptions
        if user.id in self.EXEMPT_USERS:
            return False
        
        # Judge role exempt (for hackathon demos)
        if user.role == "judge":
            return False
        
        # Only protected agents require 2FA
        return agent_id in self.PROTECTED_AGENTS
    
    async def verify_totp(self, user: User, code: str) -> bool:
        """Verify TOTP code against user's secret."""
        import pyotp
        totp = pyotp.TOTP(user.totp_secret)
        return totp.verify(code)
    
    def grant_exemption(self, admin: User, target_user_id: str):
        """Admin grants 2FA exemption to a user."""
        if admin.role != "admin":
            raise PermissionError("Only admins can grant exemptions")
        self.EXEMPT_USERS.add(target_user_id)
        # Persist to DB...

# Flow:
# 1. User clicks "Activate" on Windows agent
# 2. Check requires_2fa(user, agent_id)
# 3. If True:
#    a. Show TOTP modal in frontend
#    b. User enters 6-digit code
#    c. POST /api/agent/verify-2fa {agent_id, code}
#    d. If valid, set 15-min 2FA session cookie
# 4. Activate agent
```

**Admin Portal UI (Future):**
```
┌─────────────────────────────────────────┐
│  2FA Exemptions                         │
├─────────────────────────────────────────┤
│  ☑ judge@hackathon.com (role: judge)   │
│  ☑ demo@proxi.ai (temporary)            │
│  ☐ sarah@company.com                    │
│                                         │
│  [+ Add Exemption]                      │
└─────────────────────────────────────────┘
```

### 4.4 Per-Agent Permissions (To Implement)

```json
// backend/registry/agent_permissions.json
{
  "win-desktop": {
    "allowed_users": ["admin", "sarah"],
    "allowed_roles": ["admin"],
    "requires_2fa": true
  },
  "linux-docker": {
    "allowed_users": ["*"],
    "allowed_roles": ["*"],
    "requires_2fa": false
  }
}
```

---

## 5. Infrastructure Security

### 5.1 Cloudflare Setup

```
┌─────────────────────────────────────────────────────────────────┐
│                     CLOUDFLARE LAYER                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  DNS → Cloudflare Proxy → Origin Server                         │
│                                                                 │
│  Benefits:                                                      │
│  • DDoS protection                                              │
│  • WAF (Web Application Firewall)                               │
│  • SSL termination                                              │
│  • Bot protection                                               │
│  • Rate limiting                                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Setup Steps:**
1. Add domain to Cloudflare
2. Enable "Proxied" on DNS records
3. Set SSL mode to "Full (Strict)"
4. Enable WAF managed rules
5. Configure rate limiting rules

### 5.2 Tailscale for Agents

```
┌─────────────────────────────────────────────────────────────────┐
│                     TAILSCALE MESH                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Core Server ◄──── Encrypted Tunnel ────► Windows Agent         │
│  (100.64.0.1)                              (100.64.0.2)         │
│                                                                 │
│  Benefits:                                                      │
│  • No exposed ports                                             │
│  • WireGuard encryption                                         │
│  • Identity-based access                                        │
│  • Works behind NAT                                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 5.3 Agent Container Hardening

```dockerfile
# backend/Dockerfile.agent (security additions)

# Run as non-root
RUN adduser --disabled-password --gecos '' proxi
USER proxi

# Drop capabilities
# In docker-compose.yml:
# cap_drop:
#   - ALL
# cap_add:
#   - NET_BIND_SERVICE

# Read-only filesystem (where possible)
# read_only: true
# tmpfs:
#   - /tmp
```

---

## 6. Monitoring & Alerting

### 6.1 Security Events to Log

| Event | Severity | Action |
|-------|----------|--------|
| Failed login (3+ attempts) | Warning | Alert + temp block |
| Blocked command attempted | High | Alert + log |
| Agent activation from new IP | Medium | Log |
| Admin action | Info | Audit log |
| 2FA failure | Warning | Alert |

### 6.2 Metrics to Track

- Failed auth attempts per hour
- Blocked command frequency
- Agent activation patterns
- Session duration anomalies
- API error rates

---

## 7. Compliance Considerations

### For Future Enterprise Use

| Standard | Relevance | Key Requirements |
|----------|-----------|------------------|
| SOC2 Type II | High | Audit logs, access control, encryption |
| GDPR | Medium | Data handling, consent, deletion |
| HIPAA | Low (if healthcare) | PHI protection, BAAs |
| ISO 27001 | Medium | ISMS, risk management |

---

## 8. Incident Response Plan

### If Agent Compromised

1. **Isolate** - Deactivate agent immediately
2. **Revoke** - Rotate any exposed credentials
3. **Investigate** - Review audit logs
4. **Remediate** - Patch vulnerability
5. **Notify** - Inform affected users

### If API Key Leaked

1. **Revoke** - Regenerate Gemini API key immediately
2. **Audit** - Check for unauthorized usage
3. **Update** - Deploy new key to Core
4. **Review** - Check how leak occurred

---

*For architecture details, see [ARCHITECTURE.md](./ARCHITECTURE.md)*  
*For deployment guide, see [DEPLOY_OPS.md](./DEPLOY_OPS.md)*
