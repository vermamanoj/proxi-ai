FROM oraclelinux:9

# Install forensic tools and utilities
RUN dnf install -y \
    python3 \
    python3-pip \
    procps-ng \
    net-tools \
    iproute \
    vim \
    nano \
    grep \
    findutils \
    less \
    lsof \
    strace \
    bind-utils \
    wget \
    curl \
    gcc \
    python3-devel \
    && dnf clean all

# Set Timezone to UTC for log consistency
RUN ln -sf /usr/share/zoneinfo/UTC /etc/localtime

# Install Proxi agent dependencies
RUN pip3 install --no-cache-dir \
    fastapi==0.109.0 \
    uvicorn==0.27.0 \
    pydantic==2.6.0 \
    psutil==5.9.8

# Create the 'opc' user
RUN useradd -m -s /bin/bash opc && \
    echo "opc:OracleCloud2025!" | chpasswd

# Set up directory structure
WORKDIR /home/opc/ideaforge
RUN mkdir -p frontend backend logs .next/server/app && \
    chown -R opc:opc /home/opc/ideaforge

# Create log directories
RUN mkdir -p /var/log && \
    touch /var/log/messages /var/log/secure

# Copy scripts
COPY malware_sim.py /opt/.hidden/miner.py
COPY setup_forensics.sh /usr/local/bin/setup_forensics.sh
COPY OCI_CONSOLE_VIEW.txt /home/opc/OCI_FIREWALL_CONFIG.txt
COPY forensic_agent.py /usr/local/bin/forensic_agent.py

# Set permissions
RUN mkdir -p /opt/.hidden && \
    chmod +x /usr/local/bin/setup_forensics.sh && \
    chmod +x /opt/.hidden/miner.py && \
    chmod +x /usr/local/bin/forensic_agent.py && \
    chown opc:opc /home/opc/OCI_FIREWALL_CONFIG.txt

# Run setup
RUN /usr/local/bin/setup_forensics.sh

EXPOSE 8081

# Start Fake Miner and Agent
# The symlink trick creates a process name that looks suspicious in 'top'
CMD ["/bin/bash", "-c", "ln -sf /usr/bin/python3 /tmp/NCvhHaev && /tmp/NCvhHaev /opt/.hidden/miner.py & python3 /usr/local/bin/forensic_agent.py"]