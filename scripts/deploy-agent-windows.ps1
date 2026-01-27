# Proxi Agent Deployment Script (Windows)
# Usage: .\scripts\deploy-agent.ps1 [-Register] [-CoreUrl <url>] [-AgentName <name>]

param(
    [switch]$Register,                              # Register with Core after starting
    [string]$CoreUrl = "http://localhost:4000",     # Core server URL
    [string]$AgentName = "windows-agent",           # Agent name for registration
    [string]$AgentDescription = "Windows desktop automation agent",
    [int]$Port = 8081                               # Agent port
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Proxi Agent Deployment (Windows)" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

Set-Location $ProjectRoot

# Check Python
try {
    $pythonVersion = python --version
    Write-Host "[INFO] Found $pythonVersion" -ForegroundColor Blue
} catch {
    Write-Host "[ERROR] Python not found. Install Python 3.10+" -ForegroundColor Red
    exit 1
}

# Check/create venv
if (-not (Test-Path "venv")) {
    Write-Host "[INFO] Creating virtual environment..." -ForegroundColor Blue
    python -m venv venv
}

# Activate venv
Write-Host "[INFO] Activating virtual environment..." -ForegroundColor Blue
& "$ProjectRoot\venv\Scripts\Activate.ps1"

# Install dependencies
Write-Host "[INFO] Installing agent dependencies..." -ForegroundColor Blue
pip install -q -r backend/requirements-agent.txt

# Start agent
Write-Host "[INFO] Starting Proxi Agent on port $Port..." -ForegroundColor Blue
$agentProcess = Start-Process -FilePath "python" -ArgumentList "-m", "uvicorn", "backend.agent_server:app", "--host", "0.0.0.0", "--port", $Port -PassThru -NoNewWindow

# Wait for agent to be ready
Start-Sleep -Seconds 3

# Check agent health
try {
    $response = Invoke-WebRequest -Uri "http://localhost:$Port/health" -UseBasicParsing -TimeoutSec 5
    if ($response.StatusCode -eq 200) {
        Write-Host "[SUCCESS] Agent is running at http://localhost:$Port" -ForegroundColor Green
    }
} catch {
    Write-Host "[WARNING] Agent may not be ready yet" -ForegroundColor Yellow
}

# Register with Core if requested
if ($Register) {
    Write-Host ""
    Write-Host "[INFO] Registering agent with Core at $CoreUrl..." -ForegroundColor Blue
    
    $body = @{
        id = $AgentName
        name = "Windows Agent ($AgentName)"
        description = $AgentDescription
        workstation_type = "windows"
        host = "host.docker.internal"  # Docker can reach Windows host via this
        port = $Port
        capabilities = @("terminal", "screenshot", "desktop", "file_operations")
    } | ConvertTo-Json
    
    try {
        $response = Invoke-RestMethod -Uri "$CoreUrl/api/workstations" -Method POST -ContentType "application/json" -Body $body
        Write-Host "[SUCCESS] Agent registered: $($response.workstation.name)" -ForegroundColor Green
    } catch {
        Write-Host "[ERROR] Failed to register agent: $_" -ForegroundColor Red
        Write-Host "[INFO] You can manually register later with:" -ForegroundColor Yellow
        Write-Host "  .\scripts\register-agent.ps1 -CoreUrl $CoreUrl -AgentName $AgentName -Port $Port" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "Agent URL: http://localhost:$Port" -ForegroundColor Cyan
Write-Host "Health:    http://localhost:$Port/health" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop the agent" -ForegroundColor Yellow

# Wait for agent process
Wait-Process -Id $agentProcess.Id
