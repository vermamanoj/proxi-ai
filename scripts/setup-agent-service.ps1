# Proxi Agent Service Setup (Windows)
# Creates a scheduled task to run agent on startup (hidden console)
#
# Usage: .\scripts\setup-agent-service.ps1 [-Uninstall]

param(
    [switch]$Uninstall,
    [string]$ProjectPath = "C:\data\proxi-ai",
    [int]$Port = 8081
)

$TaskName = "ProxiAgent"
$ErrorActionPreference = "Stop"

if ($Uninstall) {
    Write-Host "Removing Proxi Agent scheduled task..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "[OK] Task removed. Agent will not start on reboot." -ForegroundColor Green
    
    # Stop any running agent
    $agentProcs = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -like "*agent_server*"
    }
    if ($agentProcs) {
        $agentProcs | Stop-Process -Force
        Write-Host "[OK] Stopped running agent process." -ForegroundColor Green
    }
    exit 0
}

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Proxi Agent Service Setup" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Verify paths
$venvPython = Join-Path $ProjectPath "venv\Scripts\pythonw.exe"  # pythonw = no console
$agentModule = "backend.agent_server:app"

if (-not (Test-Path $venvPython)) {
    Write-Host "[ERROR] Virtual environment not found at: $venvPython" -ForegroundColor Red
    Write-Host "Run: python -m venv venv && .\venv\Scripts\Activate.ps1 && pip install -r backend/requirements-agent.txt" -ForegroundColor Yellow
    exit 1
}

# Create the action - use pythonw.exe for hidden console
$action = New-ScheduledTaskAction -Execute $venvPython -Argument "-m uvicorn $agentModule --host 0.0.0.0 --port $Port" -WorkingDirectory $ProjectPath

# Trigger on logon (runs when any user logs in)
$triggerLogon = New-ScheduledTaskTrigger -AtLogOn

# Also run at startup (before login, as SYSTEM)
$triggerStartup = New-ScheduledTaskTrigger -AtStartup

# Settings
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)

# Principal - run as current user with highest privileges
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest

# Register the task
try {
    # Remove existing task if present
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    
    # Create new task with both triggers
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $triggerLogon -Settings $settings -Principal $principal -Description "Proxi AI Agent - Desktop Automation Service"
    
    Write-Host "[SUCCESS] Scheduled task created: $TaskName" -ForegroundColor Green
    Write-Host ""
    Write-Host "Agent will start automatically when you log in." -ForegroundColor Cyan
    Write-Host "Console is hidden (uses pythonw.exe)." -ForegroundColor Cyan
} catch {
    Write-Host "[ERROR] Failed to create scheduled task: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "--- Management Commands ---" -ForegroundColor Yellow
Write-Host "Start now:     Start-ScheduledTask -TaskName $TaskName" -ForegroundColor Gray
Write-Host "Stop agent:    Stop-ScheduledTask -TaskName $TaskName; Stop-Process -Name pythonw -Force" -ForegroundColor Gray
Write-Host "Check status:  Get-ScheduledTask -TaskName $TaskName | Select State" -ForegroundColor Gray
Write-Host "Uninstall:     .\scripts\setup-agent-service.ps1 -Uninstall" -ForegroundColor Gray
Write-Host ""

# Ask if user wants to start now
$startNow = Read-Host "Start agent now? (Y/n)"
if ($startNow -ne "n" -and $startNow -ne "N") {
    Start-ScheduledTask -TaskName $TaskName
    Start-Sleep -Seconds 2
    
    # Verify it's running
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$Port/health" -UseBasicParsing -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            Write-Host "[OK] Agent is running at http://localhost:$Port" -ForegroundColor Green
        }
    } catch {
        Write-Host "[WARNING] Agent may still be starting. Check: http://localhost:$Port/health" -ForegroundColor Yellow
    }
}
