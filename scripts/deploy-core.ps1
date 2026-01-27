# Proxi Core Deployment Script
# Usage: .\scripts\deploy-core.ps1 [-Rebuild] [-Logs]

param(
    [switch]$Rebuild,  # Force rebuild of Docker image
    [switch]$Logs      # Show logs after starting
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Proxi Core Deployment" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Check Docker is running
try {
    docker info | Out-Null
} catch {
    Write-Host "[ERROR] Docker is not running. Start Docker Desktop first." -ForegroundColor Red
    exit 1
}

Set-Location $ProjectRoot

# Check .env file
if (-not (Test-Path ".env")) {
    Write-Host "[WARNING] No .env file found. Creating from example..." -ForegroundColor Yellow
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "[INFO] Created .env - please edit with your API keys" -ForegroundColor Yellow
    } else {
        Write-Host "[ERROR] No .env.example found" -ForegroundColor Red
        exit 1
    }
}

# Deploy
if ($Rebuild) {
    Write-Host "[INFO] Rebuilding Core image (no cache)..." -ForegroundColor Blue
    docker compose build --no-cache core
}

Write-Host "[INFO] Starting Proxi Core..." -ForegroundColor Blue
docker compose up -d core

# Wait for startup
Write-Host "[INFO] Waiting for Core to be ready..." -ForegroundColor Blue
$attempts = 0
$maxAttempts = 30
while ($attempts -lt $maxAttempts) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:4000/api/health" -UseBasicParsing -TimeoutSec 2
        if ($response.StatusCode -eq 200) {
            Write-Host "[SUCCESS] Core is running at http://localhost:4000" -ForegroundColor Green
            break
        }
    } catch {
        $attempts++
        Start-Sleep -Seconds 1
    }
}

if ($attempts -eq $maxAttempts) {
    Write-Host "[WARNING] Core may not be fully ready. Check logs:" -ForegroundColor Yellow
    Write-Host "  docker compose logs core" -ForegroundColor Gray
}

# Show logs if requested
if ($Logs) {
    Write-Host ""
    Write-Host "[INFO] Showing Core logs (Ctrl+C to exit)..." -ForegroundColor Blue
    docker compose logs -f core
}

Write-Host ""
Write-Host "Core URL: http://localhost:4000" -ForegroundColor Cyan
Write-Host "API Docs: http://localhost:4000/docs" -ForegroundColor Cyan
