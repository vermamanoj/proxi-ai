# Proxi Windows Environment Setup Script
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   🚀 PROXI WINDOWS SETUP"
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
    # Ensure pip is available
    if (-not (Get-Command pip -ErrorAction SilentlyContinue)) {
        Write-Host "❌ Error: pip is not found." -ForegroundColor Red
        exit
    }
} else {
    Write-Host "❌ Error: Python is not installed or not in PATH." -ForegroundColor Red
    Write-Host "👉 Please install Python 3.10+ and check 'Add Python to PATH' during installation."
    exit
}

# 3. Dependency Installation
Write-Host "[1/4] Installing Python dependencies..." -ForegroundColor Yellow
if (Test-Path "backend/requirements.txt") {
    pip install -r backend/requirements.txt
} else {
    Write-Host "⚠️ Warning: backend/requirements.txt not found. Installing manually..." -ForegroundColor Yellow
}
# Explicitly ensure desktop libs are present
pip install pyautogui easyocr opencv-python pillow python-dotenv fastapi uvicorn google-generativeai psutil PyGithub

# 4. Desktop Permissions / GUI Check
Write-Host "[2/4] Testing Desktop Interaction..." -ForegroundColor Yellow
Write-Host "   Moving mouse 100px right and back..."
try {
    # Tiny snippet to test GUI session access
    python -c "import pyautogui; pyautogui.FAILSAFE=False; pyautogui.moveRel(100, 0, duration=0.5); pyautogui.moveRel(-100, 0, duration=0.5); print('GUI Access OK')"
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ GUI Session Active & Accessible." -ForegroundColor Green
    } else {
        throw "Python script failed"
    }
} catch {
    Write-Host "❌ GUI Session Error: Cannot access mouse/screen." -ForegroundColor Red
    Write-Host "👉 Ensure you are running in an interactive session (RDP/Console), not SSH/Service."
}

# 5. Environment Setup
Write-Host "[3/4] Configuring Environment..." -ForegroundColor Yellow
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

# 6. Startup Script Generation
Write-Host "[4/4] Generating Startup Script..." -ForegroundColor Yellow
$batContent = @"
@echo off
echo Starting Proxi Ghost Operator...
echo Access the frontend at http://localhost:8080 (if serving locally) or configure Nginx/Frontend separately.
cd %~dp0
call python -m uvicorn backend.main:app --host 0.0.0.0 --port 8080 --reload
pause
"@
Set-Content "run_proxi.bat" $batContent
Write-Host "✅ Generated run_proxi.bat" -ForegroundColor Green

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   🎉 Setup Complete."
Write-Host "   1. Edit '.env' to add your GEMINI_API_KEY."
Write-Host "   2. Run 'run_proxi.bat' to start the backend."
Write-Host "========================================" -ForegroundColor Cyan
