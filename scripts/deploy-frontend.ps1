# Proxi Frontend Deployment Script
# Usage: .\scripts\deploy-frontend.ps1 [-Rebuild] [-Logs]

param(
    [switch]$Rebuild,  # Force rebuild of Docker image
    [switch]$Logs      # Show logs after starting
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Proxi Frontend Deployment" -ForegroundColor Cyan
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

# Deploy
if ($Rebuild) {
    Write-Host "[INFO] Rebuilding Frontend image (no cache)..." -ForegroundColor Blue
    docker compose build --no-cache frontend
}

Write-Host "[INFO] Starting Proxi Frontend..." -ForegroundColor Blue
docker compose up -d frontend

# Wait for startup
Write-Host "[INFO] Waiting for Frontend to be ready..." -ForegroundColor Blue
$attempts = 0
$maxAttempts = 30
while ($attempts -lt $maxAttempts) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:4002" -UseBasicParsing -TimeoutSec 2
        if ($response.StatusCode -eq 200) {
            Write-Host "[SUCCESS] Frontend is running at http://localhost:4002" -ForegroundColor Green
            break
        }
    } catch {
        $attempts++
        Start-Sleep -Seconds 1
    }
}

if ($attempts -eq $maxAttempts) {
    Write-Host "[WARNING] Frontend may not be fully ready. Check logs:" -ForegroundColor Yellow
    Write-Host "  docker compose logs frontend" -ForegroundColor Gray
}

# Show logs if requested
if ($Logs) {
    Write-Host ""
    Write-Host "[INFO] Showing Frontend logs (Ctrl+C to exit)..." -ForegroundColor Blue
    docker compose logs -f frontend
}

Write-Host ""
Write-Host "Frontend URL: http://localhost:4002" -ForegroundColor Cyan
