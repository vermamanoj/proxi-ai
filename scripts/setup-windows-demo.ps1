# Proxi Windows Demo Server Setup
# Complete setup script for Windows demo environment with agent + Electron apps
#
# Usage:
#   .\scripts\setup-windows-demo.ps1                    # Install agent only
#   .\scripts\setup-windows-demo.ps1 -IncludeDemoApps   # Install agent + Electron demo apps
#   .\scripts\setup-windows-demo.ps1 -ScheduleAgent     # Install + schedule agent auto-start
#   .\scripts\setup-windows-demo.ps1 -ScheduleApps      # Install + schedule demo apps auto-start
#   .\scripts\setup-windows-demo.ps1 -All               # Everything: install + schedule all
#   .\scripts\setup-windows-demo.ps1 -Uninstall         # Remove all scheduled tasks

param(
    [switch]$IncludeDemoApps,    # Install Electron demo apps (Pricing + CRM)
    [switch]$ScheduleAgent,      # Schedule agent to auto-start on login
    [switch]$ScheduleApps,       # Schedule demo apps to auto-start on login
    [switch]$All,                # Do everything
    [switch]$Uninstall,          # Remove all scheduled tasks
    [string]$ProjectPath = "",   # Auto-detect if not specified
    [int]$Port = 8081
)

$ErrorActionPreference = "Stop"

# Auto-detect project path
if ([string]::IsNullOrEmpty($ProjectPath)) {
    $ProjectPath = Split-Path -Parent $PSScriptRoot
}

# Task names
$AgentTaskName = "ProxiAgent"
$PricingAppTaskName = "ProxiPricingApp"
$CRMAppTaskName = "ProxiCRMApp"

# Expand -All flag
if ($All) {
    $IncludeDemoApps = $true
    $ScheduleAgent = $true
    $ScheduleApps = $true
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Proxi Windows Demo Server Setup" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Project: $ProjectPath" -ForegroundColor Gray
Write-Host ""

# ============================================
# UNINSTALL
# ============================================
if ($Uninstall) {
    Write-Host "[UNINSTALL] Removing scheduled tasks..." -ForegroundColor Yellow
    
    # Stop and remove agent task
    Stop-ScheduledTask -TaskName $AgentTaskName -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $AgentTaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "  - $AgentTaskName removed" -ForegroundColor Gray
    
    # Stop and remove demo app tasks
    Stop-ScheduledTask -TaskName $PricingAppTaskName -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $PricingAppTaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "  - $PricingAppTaskName removed" -ForegroundColor Gray
    
    Stop-ScheduledTask -TaskName $CRMAppTaskName -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $CRMAppTaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "  - $CRMAppTaskName removed" -ForegroundColor Gray
    
    # Stop running processes
    Stop-Process -Name pythonw -Force -ErrorAction SilentlyContinue
    Stop-Process -Name electron -Force -ErrorAction SilentlyContinue
    
    Write-Host ""
    Write-Host "[OK] All Proxi scheduled tasks removed." -ForegroundColor Green
    exit 0
}

# ============================================
# STEP 1: Check/Install Prerequisites
# ============================================
Write-Host "[1/5] Checking prerequisites..." -ForegroundColor Blue

# Check Python
$pythonInstalled = $false
try {
    $pythonVersion = python --version 2>&1
    if ($pythonVersion -match "Python 3") {
        Write-Host "  [OK] Python: $pythonVersion" -ForegroundColor Green
        $pythonInstalled = $true
    }
} catch {}

if (-not $pythonInstalled) {
    Write-Host "  [MISSING] Python 3.10+ not found" -ForegroundColor Red
    Write-Host "  Installing Python via winget..." -ForegroundColor Yellow
    try {
        winget install Python.Python.3.12 --accept-package-agreements --accept-source-agreements
        Write-Host "  [OK] Python installed. Please restart PowerShell and run this script again." -ForegroundColor Green
        exit 0
    } catch {
        Write-Host "  [ERROR] Failed to install Python. Install manually: https://python.org" -ForegroundColor Red
        exit 1
    }
}

# Check Node.js (only if demo apps needed)
if ($IncludeDemoApps) {
    $nodeInstalled = $false
    try {
        $nodeVersion = node --version 2>&1
        if ($nodeVersion -match "v\d+") {
            Write-Host "  [OK] Node.js: $nodeVersion" -ForegroundColor Green
            $nodeInstalled = $true
        }
    } catch {}
    
    if (-not $nodeInstalled) {
        Write-Host "  [MISSING] Node.js not found" -ForegroundColor Red
        Write-Host "  Installing Node.js LTS via winget..." -ForegroundColor Yellow
        try {
            winget install OpenJS.NodeJS.LTS --accept-package-agreements --accept-source-agreements
            # Refresh PATH
            $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
            Write-Host "  [OK] Node.js installed." -ForegroundColor Green
            
            # Verify
            $nodeVersion = node --version 2>&1
            Write-Host "  [OK] Node.js: $nodeVersion" -ForegroundColor Green
        } catch {
            Write-Host "  [ERROR] Failed to install Node.js. Install manually: https://nodejs.org" -ForegroundColor Red
            Write-Host "  Then run this script again." -ForegroundColor Yellow
            exit 1
        }
    }
}

# ============================================
# STEP 2: Setup Python Virtual Environment
# ============================================
Write-Host ""
Write-Host "[2/5] Setting up Python environment..." -ForegroundColor Blue

$venvPath = Join-Path $ProjectPath "venv"
$venvPython = Join-Path $venvPath "Scripts\python.exe"
$venvPythonW = Join-Path $venvPath "Scripts\pythonw.exe"
$venvPip = Join-Path $venvPath "Scripts\pip.exe"

if (-not (Test-Path $venvPath)) {
    Write-Host "  Creating virtual environment..." -ForegroundColor Gray
    Set-Location $ProjectPath
    python -m venv venv
}

Write-Host "  Installing agent dependencies..." -ForegroundColor Gray
& $venvPip install -q -r (Join-Path $ProjectPath "backend\requirements-agent.txt")
Write-Host "  [OK] Python environment ready" -ForegroundColor Green

# ============================================
# STEP 3: Setup Electron Demo Apps (Optional)
# ============================================
if ($IncludeDemoApps) {
    Write-Host ""
    Write-Host "[3/5] Setting up Electron demo apps..." -ForegroundColor Blue
    
    $pricingAppPath = Join-Path $ProjectPath "demo-apps\pricing-app"
    $crmAppPath = Join-Path $ProjectPath "demo-apps\crm-app"
    
    # Install Pricing App dependencies
    if (Test-Path $pricingAppPath) {
        Write-Host "  Installing Pricing App dependencies..." -ForegroundColor Gray
        Set-Location $pricingAppPath
        npm install --silent 2>$null
        Write-Host "  [OK] Pricing App ready" -ForegroundColor Green
    } else {
        Write-Host "  [SKIP] Pricing App not found at: $pricingAppPath" -ForegroundColor Yellow
    }
    
    # Install CRM App dependencies
    if (Test-Path $crmAppPath) {
        Write-Host "  Installing CRM App dependencies..." -ForegroundColor Gray
        Set-Location $crmAppPath
        npm install --silent 2>$null
        Write-Host "  [OK] CRM App ready" -ForegroundColor Green
    } else {
        Write-Host "  [SKIP] CRM App not found at: $crmAppPath" -ForegroundColor Yellow
    }
    
    Set-Location $ProjectPath
} else {
    Write-Host ""
    Write-Host "[3/5] Skipping demo apps (use -IncludeDemoApps to install)" -ForegroundColor Gray
}

# ============================================
# STEP 4: Schedule Agent Auto-Start (Optional)
# ============================================
if ($ScheduleAgent) {
    Write-Host ""
    Write-Host "[4/5] Scheduling agent auto-start..." -ForegroundColor Blue
    
    # Remove existing task
    Unregister-ScheduledTask -TaskName $AgentTaskName -Confirm:$false -ErrorAction SilentlyContinue
    
    # Create action - use pythonw.exe for hidden console
    $agentAction = New-ScheduledTaskAction `
        -Execute $venvPythonW `
        -Argument "-m uvicorn backend.agent_server:app --host 0.0.0.0 --port $Port" `
        -WorkingDirectory $ProjectPath
    
    # Trigger on logon
    $agentTrigger = New-ScheduledTaskTrigger -AtLogOn
    
    # Settings with restart on failure
    $agentSettings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -RestartCount 3 `
        -RestartInterval (New-TimeSpan -Minutes 1)
    
    # Principal
    $agentPrincipal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest
    
    Register-ScheduledTask `
        -TaskName $AgentTaskName `
        -Action $agentAction `
        -Trigger $agentTrigger `
        -Settings $agentSettings `
        -Principal $agentPrincipal `
        -Description "Proxi AI Agent - Desktop Automation Service" | Out-Null
    
    Write-Host "  [OK] Agent scheduled: $AgentTaskName" -ForegroundColor Green
    Write-Host "  - Starts on login (hidden console)" -ForegroundColor Gray
    Write-Host "  - Auto-restarts on failure (3 attempts)" -ForegroundColor Gray
} else {
    Write-Host ""
    Write-Host "[4/5] Skipping agent scheduling (use -ScheduleAgent)" -ForegroundColor Gray
}

# ============================================
# STEP 5: Schedule Demo Apps Auto-Start (Optional)
# ============================================
if ($ScheduleApps -and $IncludeDemoApps) {
    Write-Host ""
    Write-Host "[5/5] Scheduling demo apps auto-start..." -ForegroundColor Blue
    
    $npmPath = (Get-Command npm -ErrorAction SilentlyContinue).Source
    if (-not $npmPath) {
        $npmPath = "npm"
    }
    
    # Pricing App
    $pricingAppPath = Join-Path $ProjectPath "demo-apps\pricing-app"
    if (Test-Path $pricingAppPath) {
        Unregister-ScheduledTask -TaskName $PricingAppTaskName -Confirm:$false -ErrorAction SilentlyContinue
        
        $pricingAction = New-ScheduledTaskAction `
            -Execute $npmPath `
            -Argument "start" `
            -WorkingDirectory $pricingAppPath
        
        $pricingTrigger = New-ScheduledTaskTrigger -AtLogOn
        $pricingSettings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
        
        Register-ScheduledTask `
            -TaskName $PricingAppTaskName `
            -Action $pricingAction `
            -Trigger $pricingTrigger `
            -Settings $pricingSettings `
            -Description "Proxi Demo - Pricing App" | Out-Null
        
        Write-Host "  [OK] Pricing App scheduled: $PricingAppTaskName" -ForegroundColor Green
    }
    
    # CRM App
    $crmAppPath = Join-Path $ProjectPath "demo-apps\crm-app"
    if (Test-Path $crmAppPath) {
        Unregister-ScheduledTask -TaskName $CRMAppTaskName -Confirm:$false -ErrorAction SilentlyContinue
        
        $crmAction = New-ScheduledTaskAction `
            -Execute $npmPath `
            -Argument "start" `
            -WorkingDirectory $crmAppPath
        
        $crmTrigger = New-ScheduledTaskTrigger -AtLogOn
        $crmSettings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
        
        Register-ScheduledTask `
            -TaskName $CRMAppTaskName `
            -Action $crmAction `
            -Trigger $crmTrigger `
            -Settings $crmSettings `
            -Description "Proxi Demo - CRM App" | Out-Null
        
        Write-Host "  [OK] CRM App scheduled: $CRMAppTaskName" -ForegroundColor Green
    }
} elseif ($ScheduleApps) {
    Write-Host ""
    Write-Host "[5/5] Skipping app scheduling (need -IncludeDemoApps)" -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "[5/5] Skipping app scheduling (use -ScheduleApps)" -ForegroundColor Gray
}

# ============================================
# SUMMARY
# ============================================
Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  Setup Complete!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""

# Show what was installed
Write-Host "Installed:" -ForegroundColor Cyan
Write-Host "  - Python environment with agent dependencies" -ForegroundColor Gray
if ($IncludeDemoApps) {
    Write-Host "  - Electron demo apps (Pricing + CRM)" -ForegroundColor Gray
}

# Show what was scheduled
if ($ScheduleAgent -or $ScheduleApps) {
    Write-Host ""
    Write-Host "Scheduled Tasks (auto-start on login):" -ForegroundColor Cyan
    if ($ScheduleAgent) {
        Write-Host "  - $AgentTaskName (port $Port, hidden console)" -ForegroundColor Gray
    }
    if ($ScheduleApps -and $IncludeDemoApps) {
        Write-Host "  - $PricingAppTaskName" -ForegroundColor Gray
        Write-Host "  - $CRMAppTaskName" -ForegroundColor Gray
    }
}

# Management commands
Write-Host ""
Write-Host "--- Management Commands ---" -ForegroundColor Yellow
Write-Host "Start all now:" -ForegroundColor Gray
if ($ScheduleAgent) {
    Write-Host "  Start-ScheduledTask -TaskName $AgentTaskName" -ForegroundColor DarkGray
}
if ($ScheduleApps -and $IncludeDemoApps) {
    Write-Host "  Start-ScheduledTask -TaskName $PricingAppTaskName" -ForegroundColor DarkGray
    Write-Host "  Start-ScheduledTask -TaskName $CRMAppTaskName" -ForegroundColor DarkGray
}
Write-Host ""
Write-Host "Stop all:" -ForegroundColor Gray
Write-Host "  Stop-Process -Name pythonw,electron -Force -ErrorAction SilentlyContinue" -ForegroundColor DarkGray
Write-Host ""
Write-Host "Uninstall all:" -ForegroundColor Gray
Write-Host "  .\scripts\setup-windows-demo.ps1 -Uninstall" -ForegroundColor DarkGray
Write-Host ""

# Ask if user wants to start now
$startNow = Read-Host "Start everything now? (Y/n)"
if ($startNow -ne "n" -and $startNow -ne "N") {
    Write-Host ""
    Write-Host "Starting services..." -ForegroundColor Blue
    
    if ($ScheduleAgent) {
        Start-ScheduledTask -TaskName $AgentTaskName -ErrorAction SilentlyContinue
        Write-Host "  - Agent starting..." -ForegroundColor Gray
    } else {
        # Start agent manually in background
        Write-Host "  - Starting agent manually..." -ForegroundColor Gray
        Start-Process -FilePath $venvPythonW -ArgumentList "-m uvicorn backend.agent_server:app --host 0.0.0.0 --port $Port" -WorkingDirectory $ProjectPath -WindowStyle Hidden
    }
    
    if ($ScheduleApps -and $IncludeDemoApps) {
        Start-ScheduledTask -TaskName $PricingAppTaskName -ErrorAction SilentlyContinue
        Start-ScheduledTask -TaskName $CRMAppTaskName -ErrorAction SilentlyContinue
        Write-Host "  - Demo apps starting..." -ForegroundColor Gray
    } elseif ($IncludeDemoApps) {
        # Start apps manually
        Write-Host "  - Starting demo apps manually..." -ForegroundColor Gray
        Start-Process -FilePath "npm" -ArgumentList "start" -WorkingDirectory (Join-Path $ProjectPath "demo-apps\pricing-app") -WindowStyle Minimized
        Start-Process -FilePath "npm" -ArgumentList "start" -WorkingDirectory (Join-Path $ProjectPath "demo-apps\crm-app") -WindowStyle Minimized
    }
    
    Start-Sleep -Seconds 3
    
    # Verify agent
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$Port/health" -UseBasicParsing -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            Write-Host ""
            Write-Host "[OK] Agent running at http://localhost:$Port" -ForegroundColor Green
        }
    } catch {
        Write-Host ""
        Write-Host "[INFO] Agent may still be starting. Check: http://localhost:$Port/health" -ForegroundColor Yellow
    }
}

Write-Host ""
