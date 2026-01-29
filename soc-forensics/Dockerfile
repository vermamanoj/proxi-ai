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

# Install Proxi agent dependencies
RUN pip3 install --no-cache-dir \
    fastapi==0.109.0 \
    uvicorn==0.27.0 \
    pydantic==2.6.0 \
    psutil==5.9.8

# Create the 'opc' user (Standard Oracle Cloud user)
RUN useradd -m -s /bin/bash opc && \
    echo "opc:OracleCloud2025!" | chpasswd

# Set up directory structure for IdeaForge application
WORKDIR /home/opc/ideaforge
RUN mkdir -p frontend backend logs .next/server/app && \
    chown -R opc:opc /home/opc/ideaforge

# Create log directories
RUN mkdir -p /var/log && \
    touch /var/log/messages /var/log/secure

# Copy simulation scripts
COPY fake_miner.py /usr/local/bin/fake_miner.py
COPY setup_forensics.sh /usr/local/bin/setup_forensics.sh
COPY OCI_CONSOLE_VIEW.txt /home/opc/OCI_FIREWALL_CONFIG.txt
COPY forensic_agent.py /usr/local/bin/forensic_agent.py

# Set permissions
RUN chmod +x /usr/local/bin/setup_forensics.sh && \
    chmod +x /usr/local/bin/fake_miner.py && \
    chmod +x /usr/local/bin/forensic_agent.py && \
    chown opc:opc /home/opc/OCI_FIREWALL_CONFIG.txt

# Run the setup script to generate logs and artifacts
RUN /usr/local/bin/setup_forensics.sh

# Expose port for Proxi agent
EXPOSE 8081

# Start fake miner and Proxi agent on container startup
CMD ["/bin/bash", "-c", "python3 /usr/local/bin/fake_miner.py & python3 /usr/local/bin/forensic_agent.py"]
