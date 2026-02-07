# Proxi Agent Deployment Script (Windows)
# Usage: .\scripts\deploy-agent-windows.ps1 [-Register] [-Diagnose] [-CoreUrl <url>]

param(
    [switch]$Register,                              # Register with Core after starting
    [switch]$Diagnose,                              # Run diagnostics only (don't start agent)
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

# ============================================
# DIAGNOSE MODE: Check all dependencies
# ============================================
if ($Diagnose) {
    Write-Host ""
    Write-Host "============================================" -ForegroundColor Yellow
    Write-Host "  DEPENDENCY DIAGNOSTICS" -ForegroundColor Yellow
    Write-Host "============================================" -ForegroundColor Yellow
    
    $criticalPackages = @(
        @{Name="pyautogui"; Import="pyautogui"; Purpose="Mouse/keyboard automation"},
        @{Name="pywinauto"; Import="pywinauto"; Purpose="Window management, UI tree"},
        @{Name="opencv-python"; Import="cv2"; Purpose="Screenshot processing"},
        @{Name="google-generativeai"; Import="google.generativeai"; Purpose="Visual grounding"},
        @{Name="psutil"; Import="psutil"; Purpose="System metrics"},
        @{Name="fastapi"; Import="fastapi"; Purpose="Agent HTTP server"}
    )
    
    $missing = @()
    foreach ($pkg in $criticalPackages) {
        $result = python -c "import importlib.util; print('OK' if importlib.util.find_spec('$($pkg.Import)') else 'MISSING')" 2>&1
        if ($result -eq "OK") {
            Write-Host "  ✅ $($pkg.Name) - $($pkg.Purpose)" -ForegroundColor Green
        } else {
            Write-Host "  ❌ $($pkg.Name) MISSING - $($pkg.Purpose)" -ForegroundColor Red
            $missing += $pkg.Name
        }
    }
    
    # Test pywinauto window enumeration
    Write-Host ""
    Write-Host "Testing window enumeration..." -ForegroundColor Yellow
    $windowTest = python -c "
try:
    from pywinauto import Desktop
    d = Desktop(backend='uia')
    w = d.windows(visible_only=True)
    print(f'OK:{len(w)} windows')
except Exception as e:
    print(f'FAIL:{e}')
" 2>&1
    if ($windowTest -match "^OK:") {
        Write-Host "  ✅ Window enumeration: $windowTest" -ForegroundColor Green
    } else {
        Write-Host "  ❌ Window enumeration: $windowTest" -ForegroundColor Red
    }
    
    # Check .env
    Write-Host ""
    if (Test-Path ".env") {
        $envContent = Get-Content ".env" -Raw
        if ($envContent -match "GEMINI_API_KEY=\S+") {
            Write-Host "  ✅ GEMINI_API_KEY configured in .env" -ForegroundColor Green
        } else {
            Write-Host "  ⚠️ GEMINI_API_KEY not set in .env (ground_and_click won't work)" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  ⚠️ No .env file found" -ForegroundColor Yellow
    }
    
    if ($missing.Count -gt 0) {
        Write-Host ""
        Write-Host "Run without -Diagnose to install missing packages from requirements-agent.txt" -ForegroundColor Cyan
    }
    exit 0
}

# Install dependencies from requirements file
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
