# Proxi Security Guardrails

> **For Hackathon Judges:** This document explains Proxi's security-first approach to OS-level AI automation.

## Overview

Unlike browser-based AI agents that only interact with web DOM, Proxi has **full OS control** - it can run terminal commands, manage processes, and automate desktop applications. This power requires robust security guardrails.

## Three-Tier Command Security

Proxi implements a **three-tier security model** for all terminal commands:

### 🔴 BLOCKED (Always Denied)

Commands that could cause catastrophic damage are **always blocked**, even if the user or AI requests them:

| Category | Examples | Why Blocked |
|----------|----------|-------------|
| System Destruction | `rm -rf /`, `format C:`, `dd if=/dev/zero` | Irreversible data loss |
| Boot/Recovery | `bcdedit /delete`, `grub-install` | System unbootable |
| Fork Bombs | `:(){ :\|:&};:`, `%0\|%0` | Resource exhaustion |
| Credential Attacks | `passwd root`, `net user administrator` | Privilege escalation |
| Firewall Bypass | `iptables -F`, `netsh firewall off` | Security compromise |

**Total: 37 blocked patterns** covering Windows, Linux, and cross-platform attacks.

### 🟡 APPROVAL REQUIRED (Human-in-the-Loop)

Sensitive but legitimate operations require explicit user approval:

| Category | Examples | Risk Level |
|----------|----------|------------|
| Package Installation | `pip install`, `npm install -g`, `apt install` | Supply chain risk |
| Process Termination | `taskkill`, `kill -9`, `pkill` | Service disruption |
| Service Control | `net stop`, `systemctl stop` | Availability impact |
| File Deletion | `rm`, `del`, `Remove-Item` | Data loss |
| User Management | `useradd`, `userdel` | Access control |
| Permission Changes | `chmod`, `chown`, `icacls` | Security posture |
| Scheduled Tasks | `schtasks`, `crontab` | Persistence |

**Total: 42 approval-required patterns.**

### 🟢 SAFE (Auto-Approved)

Read-only and non-destructive operations run without interruption:

| Category | Examples |
|----------|----------|
| Directory Listing | `ls`, `dir`, `Get-ChildItem` |
| File Viewing | `cat`, `type`, `Get-Content` |
| System Info | `whoami`, `hostname`, `systeminfo` |
| Process Viewing | `ps`, `top`, `Get-Process` |
| Network Info | `netstat`, `ipconfig`, `ping` |
| Git Read-Only | `git status`, `git log`, `git diff` |

**Total: 76 safe patterns.**

## File Path Protection

In addition to command patterns, Proxi protects sensitive file paths:

```
🔒 Protected Paths:
- /etc/shadow, /etc/passwd, /etc/sudoers
- ~/.ssh/*, ~/.gnupg/*
- C:\Windows\System32\config\*
- .env, .credentials, *_secret*
- *.pem, *.key, id_rsa*
```

## Modes of Operation

### Strict Mode (Production)
- Unknown commands require approval
- All security checks enforced
- Full audit logging

### Permissive Mode (Development)
- Unknown commands auto-approved
- Blocked commands still denied
- Reduced friction for trusted environments

### Dev Mode (`PROXI_DEV_MODE=true`)
- Skips approval prompts (for demos/sandboxes)
- **Blocked commands still enforced**
- Logs all bypassed approvals

## User Override (`!` Prefix)

Users can bypass the AI's approval flow for legitimate operations:

```
User: !taskkill /PID 1234
→ Executes immediately (bypasses approval)
→ Added to AI context (AI knows user killed process)

User: !rm -rf /
→ STILL BLOCKED (catastrophic commands never allowed)
```

This enables power users while maintaining safety rails.

## Implementation Details

- **File:** `backend/tools/command_guard.py` (682 lines)
- **Classes:** `CommandGuard`, `FileGuard`
- **Integration:** Called before every `run_terminal_command()` execution

## For Judges: Why This Matters

1. **Trust**: Users can delegate OS tasks to AI without fear of accidental damage
2. **Compliance**: Audit trail for all sensitive operations
3. **Safety**: Multiple layers prevent catastrophic mistakes
4. **Usability**: Safe operations run instantly, only risky ones pause

## Example Flow

```
User: "Kill the runaway Python process using too much CPU"

AI: Checking processes...
    → get_process_list() [SAFE] ✓ Auto-run

AI: Found python.exe (PID 5432) at 98% CPU
    → taskkill /PID 5432 [NEEDS_APPROVAL]
    
    ⚠️ This command requires approval:
    "Process termination - taskkill"
    
    [Approve] [Deny]

User: [Approve]

AI: Process terminated successfully.
    → verify_process_killed(5432) [SAFE] ✓ Auto-run
    ✓ Verified: Process no longer running
```

---

*Proxi: Full OS control with security you can trust.*
