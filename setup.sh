#!/bin/bash

# Setup Script for Proxi Environment (Ubuntu)
# Usage: sudo bash setup.sh

set -e

echo "========================================"
echo "   🛠️  PROXI SERVER SETUP"
echo "========================================"

# 1. Update Apt
echo "[1/4] Updating package database..."
sudo apt-get update

# 2. Install Nginx
echo "[2/4] Installing Nginx..."
sudo apt-get install -y nginx
sudo systemctl enable nginx
sudo systemctl start nginx

# 3. Install Docker & Docker Compose
echo "[3/4] Installing Docker..."
if ! command -v docker &> /dev/null; then
    sudo apt-get install -y ca-certificates curl gnupg
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg

    echo \
      "deb [arch=\"$(dpkg --print-architecture)\" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(. /etc/os-release && echo \"$VERSION_CODENAME\") stable" | \
      sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
else
    echo " -> Docker already installed."
fi

# 4. Permissions
echo "[4/4] Configuring permissions..."
# Add current user to docker group to avoid using sudo for docker commands
sudo usermod -aG docker $USER

echo "========================================"
echo "   ✅ Setup Complete."
echo "   ⚠️  Please LOG OUT and LOG BACK IN for Docker permissions to take effect."
echo "========================================"
