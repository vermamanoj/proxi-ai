# Proxi Windows Agent Registration Script
# Usage: .\scripts\register-windows-agent.ps1
#
# This script:
# 1. Starts the Windows agent locally
# 2. Guides you to register it with the production server
#
# Prerequisites:
# - Tailscale installed and connected on both machines
# - Python 3.10+ with venv

param(
    [string]$AgentName = "win-desktop",
    [string]$AgentDisplayName = "Windows Desktop",
    [int]$Port = 8081
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  Proxi Windows Agent Setup" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check Tailscale
Write-Host "[1/4] Checking Tailscale..." -ForegroundColor Yellow
try {
    $tailscaleIP = (tailscale ip -4 2>$null)
    if ($tailscaleIP) {
        Write-Host "  Tailscale IP: $tailscaleIP" -ForegroundColor Green
    } else {
        Write-Host "  [WARNING] Tailscale not connected!" -ForegroundColor Red
        Write-Host "  Install: winget install Tailscale.Tailscale" -ForegroundColor Gray
        Write-Host "  Then connect via system tray icon" -ForegroundColor Gray
        exit 1
    }
} catch {
    Write-Host "  [WARNING] Tailscale not installed" -ForegroundColor Red
    Write-Host "  Install: winget install Tailscale.Tailscale" -ForegroundColor Gray
    exit 1
}

# Step 2: Check/Setup Python environment
Write-Host ""
Write-Host "[2/4] Setting up Python environment..." -ForegroundColor Yellow
Set-Location $ProjectRoot

if (-not (Test-Path "venv")) {
    Write-Host "  Creating virtual environment..." -ForegroundColor Gray
    python -m venv venv
}

& "$ProjectRoot\venv\Scripts\Activate.ps1"
pip install -q -r backend/requirements-agent.txt 2>$null
Write-Host "  Python environment ready" -ForegroundColor Green

# Step 3: Set agent key
Write-Host ""
Write-Host "[3/4] Agent Security..." -ForegroundColor Yellow
$agentKey = $env:PROXI_AGENT_KEY
if (-not $agentKey) {
    Write-Host "  [WARNING] PROXI_AGENT_KEY not set!" -ForegroundColor Red
    Write-Host "  Set it to match your production server's .env:" -ForegroundColor Gray
    Write-Host '  $env:PROXI_AGENT_KEY = "your-key-here"' -ForegroundColor Gray
    Write-Host ""
    $continue = Read-Host "  Continue without agent key? (y/N)"
    if ($continue -ne "y") { exit 1 }
} else {
    Write-Host "  Agent key configured" -ForegroundColor Green
}

# Step 4: Start agent
Write-Host ""
Write-Host "[4/4] Starting agent on port $Port..." -ForegroundColor Yellow
Write-Host ""

# Show registration instructions
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  NEXT STEPS" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Log in to Proxi as ADMIN at https://proxi.audista.com" -ForegroundColor White
Write-Host ""
Write-Host "2. Open Settings > Admin Panel (or use curl below)" -ForegroundColor White
Write-Host ""
Write-Host "3. Register this agent with Tailscale IP:" -ForegroundColor White
Write-Host ""
Write-Host "   Agent ID:   $AgentName" -ForegroundColor Green
Write-Host "   Agent Name: $AgentDisplayName" -ForegroundColor Green
Write-Host "   Host:       $tailscaleIP" -ForegroundColor Green
Write-Host "   Port:       $Port" -ForegroundColor Green
Write-Host ""
Write-Host "4. Or add manually to workstations.json on server:" -ForegroundColor White
Write-Host ""
Write-Host @"
   "$AgentName": {
     "id": "$AgentName",
     "name": "$AgentDisplayName",
     "host": "$tailscaleIP",
     "port": $Port,
     "workstation_type": "windows",
     "capabilities": ["terminal", "screenshot", "desktop", "file_operations"]
   }
"@ -ForegroundColor Gray
Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  Agent starting... Press Ctrl+C to stop" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Start agent (blocking)
python -m uvicorn backend.agent_server:app --host 0.0.0.0 --port $Port
