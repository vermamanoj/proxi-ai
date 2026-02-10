# Zero-Downtime Deployment Script for Proxi
# Strategy: Build first, then quick restart with health check wait
# 
# Usage: .\deploy-zero-downtime.ps1 [service]
# Example: .\deploy-zero-downtime.ps1 core
#          .\deploy-zero-downtime.ps1 frontend
#          .\deploy-zero-downtime.ps1 all

param(
    [string]$Service = "all"
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

Write-Host "=== Zero-Downtime Deploy: $Service ===" -ForegroundColor Cyan

function Wait-ForHealth {
    param([string]$url, [int]$maxWait = 60)
    
    $attempts = 0
    while ($attempts -lt $maxWait) {
        try {
            $response = Invoke-WebRequest -Uri $url -TimeoutSec 2 -UseBasicParsing -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200) {
                return $true
            }
        } catch {}
        Start-Sleep -Seconds 1
        $attempts++
        Write-Host "." -NoNewline
    }
    return $false
}

function Deploy-Service {
    param([string]$svc, [string]$healthUrl)
    
    Write-Host "`n[$svc] Building new image (app stays up during build)..." -ForegroundColor Yellow
    docker-compose build $svc
    if ($LASTEXITCODE -ne 0) { throw "Build failed" }
    
    Write-Host "[$svc] Quick restart with new image..." -ForegroundColor Yellow
    docker-compose up -d --no-deps --force-recreate $svc
    
    Write-Host "[$svc] Waiting for health " -NoNewline -ForegroundColor Yellow
    $healthy = Wait-ForHealth $healthUrl
    Write-Host ""
    
    if (-not $healthy) {
        Write-Host "[$svc] WARNING: Health check timed out, check logs" -ForegroundColor Red
        docker-compose logs --tail 20 $svc
    } else {
        Write-Host "[$svc] Deployed successfully!" -ForegroundColor Green
    }
}

# Pull latest code first (no downtime)
Write-Host "`nPulling latest code..." -ForegroundColor Yellow
git pull

$services = @{
    "core" = "http://localhost:4000/api/health"
    "agent" = "http://localhost:4001/health"
    "frontend" = "http://localhost:4002"
}

if ($Service -eq "all") {
    foreach ($svc in @("core", "agent", "frontend")) {
        Deploy-Service $svc $services[$svc]
    }
} elseif ($services.ContainsKey($Service)) {
    Deploy-Service $Service $services[$Service]
} else {
    Write-Host "Unknown service: $Service. Use: core, agent, frontend, or all" -ForegroundColor Red
    exit 1
}

Write-Host "`n=== Deployment Complete ===" -ForegroundColor Green
docker-compose ps
