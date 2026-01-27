# Proxi Full Stack Deployment Script
# Deploys Core + Frontend (Docker) and optionally the local Windows Agent
#
# Usage: .\scripts\deploy-all.ps1 [-Rebuild] [-IncludeAgent]

param(
    [switch]$Rebuild,       # Force rebuild all Docker images
    [switch]$IncludeAgent,  # Also start and register local Windows agent
    [switch]$CleanData      # Clear persistent data (database, logs)
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Proxi Full Stack Deployment" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

Set-Location $ProjectRoot

# Check Docker
try {
    docker info | Out-Null
    Write-Host "[OK] Docker is running" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Docker is not running. Start Docker Desktop first." -ForegroundColor Red
    exit 1
}

# Clean data if requested
if ($CleanData) {
    Write-Host "[INFO] Cleaning persistent data..." -ForegroundColor Yellow
    if (Test-Path "data") {
        Remove-Item -Recurse -Force "data\*" -ErrorAction SilentlyContinue
    }
}

# Check .env
if (-not (Test-Path ".env")) {
    Write-Host "[WARNING] No .env file. Creating from example..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env" -ErrorAction SilentlyContinue
    Write-Host "[ACTION REQUIRED] Edit .env with your GEMINI_API_KEY" -ForegroundColor Red
    exit 1
}

# Deploy Docker services
Write-Host ""
Write-Host "--- Deploying Docker Services ---" -ForegroundColor Cyan

if ($Rebuild) {
    Write-Host "[INFO] Rebuilding all images (no cache)..." -ForegroundColor Blue
    docker compose build --no-cache
} else {
    docker compose build
}

Write-Host "[INFO] Starting Core and Frontend..." -ForegroundColor Blue
docker compose up -d core frontend

# Wait for services
Write-Host "[INFO] Waiting for services to be ready..." -ForegroundColor Blue
Start-Sleep -Seconds 5

# Check Core
$coreReady = $false
for ($i = 0; $i -lt 20; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:4000/api/health" -UseBasicParsing -TimeoutSec 2
        if ($response.StatusCode -eq 200) {
            Write-Host "[OK] Core is ready" -ForegroundColor Green
            $coreReady = $true
            break
        }
    } catch {
        Start-Sleep -Seconds 1
    }
}
if (-not $coreReady) {
    Write-Host "[WARNING] Core may not be ready. Check: docker compose logs core" -ForegroundColor Yellow
}

# Check Frontend
$frontendReady = $false
for ($i = 0; $i -lt 20; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:4002" -UseBasicParsing -TimeoutSec 2
        if ($response.StatusCode -eq 200) {
            Write-Host "[OK] Frontend is ready" -ForegroundColor Green
            $frontendReady = $true
            break
        }
    } catch {
        Start-Sleep -Seconds 1
    }
}
if (-not $frontendReady) {
    Write-Host "[WARNING] Frontend may not be ready. Check: docker compose logs frontend" -ForegroundColor Yellow
}

# Deploy local agent if requested
if ($IncludeAgent) {
    Write-Host ""
    Write-Host "--- Deploying Local Windows Agent ---" -ForegroundColor Cyan
    
    # Check venv
    if (-not (Test-Path "venv")) {
        Write-Host "[INFO] Creating virtual environment..." -ForegroundColor Blue
        python -m venv venv
    }
    
    # Activate and install
    & "$ProjectRoot\venv\Scripts\Activate.ps1"
    pip install -q -r backend/requirements-agent.txt
    
    # Start agent in background
    Write-Host "[INFO] Starting Windows Agent..." -ForegroundColor Blue
    Start-Process -FilePath "powershell" -ArgumentList "-Command", "& '$ProjectRoot\venv\Scripts\Activate.ps1'; python -m uvicorn backend.agent_server:app --host 0.0.0.0 --port 8081" -WindowStyle Minimized
    
    Start-Sleep -Seconds 3
    
    # Register agent
    & "$ProjectRoot\scripts\register-agent.ps1" -AgentName "windows-local" -DisplayName "Windows Agent (Local)" -Port 8081
}

# Summary
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Deployment Complete!" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Frontend:  http://localhost:4002" -ForegroundColor White
Write-Host "  Core API:  http://localhost:4000" -ForegroundColor White
Write-Host "  API Docs:  http://localhost:4000/docs" -ForegroundColor White
if ($IncludeAgent) {
    Write-Host "  Agent:     http://localhost:8081" -ForegroundColor White
}
Write-Host ""
Write-Host "--- Useful Commands ---" -ForegroundColor Yellow
Write-Host "  View logs:     docker compose logs -f" -ForegroundColor Gray
Write-Host "  Stop all:      docker compose down" -ForegroundColor Gray
Write-Host "  Restart:       docker compose restart" -ForegroundColor Gray
Write-Host ""
