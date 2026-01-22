#!/bin/bash

# Proxi Deployment Script

echo "Starting Deployment..."

# 1. Frontend Build
# Check if 'frontend' directory exists (repo structure) vs root (flat structure)
if [ -d "frontend" ]; then
    echo "Entering frontend directory..."
    cd frontend
fi

echo "Installing frontend dependencies..."
# Force development environment to ensure devDependencies (like Vite) are installed
# This overrides any global NODE_ENV=production setting in Cloud Shell
export NODE_ENV=development
npm install

if [ $? -ne 0 ]; then
    echo "Error: npm install failed."
    exit 1
fi

echo "Building frontend..."
npm run build

if [ ! -d "dist" ]; then
    echo "Error: dist/ directory not found. Build failed."
    exit 1
fi

# If we entered a subdirectory, move back to root to access backend
if [ -f "../backend/main.py" ]; then
    cd ..
fi

# 2. Backend Prep
echo "Preparing backend static files..."
mkdir -p backend/static

# Clean old files
rm -rf backend/static/*

# Copy build artifacts to backend
if [ -d "frontend/dist" ]; then
    cp -r frontend/dist/* backend/static/
elif [ -d "dist" ]; then
    cp -r dist/* backend/static/
else
    echo "Error: Could not locate dist folder to copy."
    exit 1
fi

# 3. Python Dependencies
echo "Installing Python dependencies..."
pip install -r backend/requirements.txt -q

# 4. Execution
echo "Restarting application..."

# Kill any existing process on port 8080
if command -v fuser >/dev/null; then
    fuser -k 8080/tcp > /dev/null 2>&1
else
    # Fallback if fuser is missing
    echo "Warning: fuser not found, skipping port kill."
fi

# Start uvicorn in background
nohup python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8080 > server.log 2>&1 &

echo "Proxi is Live! Monitor logs with: tail -f server.log"