# Proxi Windows Environment Setup Script
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   🚀 PROXI WINDOWS SETUP (ISOLATED)"
Write-Host "========================================" -ForegroundColor Cyan

# 1. Privilege Check
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
if (-not $isAdmin) {
    Write-Host "❌ Error: This script requires Administrator privileges." -ForegroundColor Red
    Write-Host "👉 Please right-click and 'Run as Administrator'."
    exit
}
Write-Host "✅ Administrator privileges confirmed." -ForegroundColor Green

# 2. Python Check
if (Get-Command python -ErrorAction SilentlyContinue) {
    $pyVersion = python --version 2>&1
    Write-Host "✅ Python found: $pyVersion" -ForegroundColor Green
} else {
    Write-Host "❌ Error: Python is not installed or not in PATH." -ForegroundColor Red
    Write-Host "👉 Please install Python 3.10+ and check 'Add Python to PATH' during installation."
    exit
}

# 3. Virtual Environment Setup
Write-Host "[1/5] Setting up Virtual Environment..." -ForegroundColor Yellow
if (-not (Test-Path "venv")) {
    Write-Host "   Creating 'venv' folder..."
    python -m venv venv
    if (-not $?) {
        Write-Host "❌ Failed to create venv." -ForegroundColor Red
        exit
    }
} else {
    Write-Host "   'venv' already exists."
}

# Define paths to venv executables
$VenvPython = ".\venv\Scripts\python.exe"
$VenvPip = ".\venv\Scripts\pip.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Host "❌ Error: Virtual Environment not created correctly." -ForegroundColor Red
    exit
}

# 4. Dependency Installation (Inside Venv)
Write-Host "[2/5] Installing dependencies into venv..." -ForegroundColor Yellow
# Upgrade pip first
& $VenvPython -m pip install --upgrade pip

if (Test-Path "backend/requirements.txt") {
    & $VenvPip install -r backend/requirements.txt
} else {
    Write-Host "⚠️ Warning: backend/requirements.txt not found." -ForegroundColor Yellow
}
# Explicitly ensure desktop libs are present
& $VenvPip install pyautogui easyocr opencv-python pillow python-dotenv fastapi uvicorn google-generativeai psutil PyGithub

# 5. Desktop Permissions / GUI Check
Write-Host "[3/5] Testing Desktop Interaction..." -ForegroundColor Yellow
try {
    # Run the test using the VENV python
    & $VenvPython -c "import pyautogui; pyautogui.FAILSAFE=False; pyautogui.moveRel(10, 0, duration=0.2); pyautogui.moveRel(-10, 0, duration=0.2); print('GUI Access OK')"
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ GUI Session Active & Accessible." -ForegroundColor Green
    } else {
        throw "Python script failed"
    }
} catch {
    Write-Host "❌ GUI Session Error: Cannot access mouse/screen." -ForegroundColor Red
    Write-Host "👉 Ensure you are running in an interactive session (RDP/Console), not SSH/Service."
}

# 6. Environment Setup
Write-Host "[4/5] Configuring Environment..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    Write-Host "Creating .env template..."
    $envContent = @"
GEMINI_API_KEY=your_api_key_here
GITHUB_TOKEN=your_github_token_here
"@
    Set-Content ".env" $envContent
    Write-Host "⚠️ Created .env file. YOU MUST EDIT IT with your API keys!" -ForegroundColor Magenta
} else {
    Write-Host "✅ .env file exists." -ForegroundColor Green
}

# 7. Startup Script Generation
Write-Host "[5/5] Generating Startup Script..." -ForegroundColor Yellow
# We generate a bat file that uses the venv python explicitly
$batContent = @"
@echo off
echo Starting Proxi Ghost Operator (Virtual Env)...
cd %~dp0
call venv\Scripts\activate
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8080 --reload
pause
"@
Set-Content "run_proxi.bat" $batContent
Write-Host "✅ Generated run_proxi.bat" -ForegroundColor Green

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   🎉 Setup Complete."
Write-Host "   1. Edit '.env' to add your keys."
Write-Host "   2. Run 'run_proxi.bat' to start (Uses local venv)."
Write-Host "========================================" -ForegroundColor Cyan
