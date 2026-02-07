# Proxi Windows Agent - Quick Fix Dependencies
# Run this on the Windows agent machine to install all required packages
# Usage: .\scripts\fix-windows-agent-deps.ps1

param(
    [switch]$CreateEnv,
    [string]$GeminiApiKey = ""
)

Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "  PROXI WINDOWS AGENT - DEPENDENCY FIX" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""

# Check if venv exists
$venvPath = ".\venv"
if (-not (Test-Path "$venvPath\Scripts\python.exe")) {
    Write-Host "[!] No virtual environment found. Creating one..." -ForegroundColor Yellow
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to create virtual environment" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ Virtual environment created" -ForegroundColor Green
}

# Activate venv
Write-Host "[1/4] Activating virtual environment..." -ForegroundColor Yellow
& "$venvPath\Scripts\Activate.ps1"

# Upgrade pip
Write-Host "[2/4] Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip

# Install all required packages
Write-Host "[3/4] Installing required packages..." -ForegroundColor Yellow
$packages = @(
    # Core automation
    "pyautogui",
    "pywinauto",
    "pywin32",
    
    # Image processing
    "opencv-python",
    "numpy",
    "Pillow",
    
    # Clipboard
    "pyperclip",
    
    # AI/Vision
    "google-generativeai",
    
    # Server
    "fastapi",
    "uvicorn[standard]",
    
    # System
    "psutil",
    "python-dotenv",
    
    # HTTP
    "httpx",
    "requests"
)

$packageList = $packages -join " "
Write-Host "  Installing: $packageList" -ForegroundColor Gray
pip install $packages

if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️ Some packages may have failed to install" -ForegroundColor Yellow
} else {
    Write-Host "✅ All packages installed successfully" -ForegroundColor Green
}

# Create .env file if requested
Write-Host "[4/4] Checking .env file..." -ForegroundColor Yellow
if ($CreateEnv -or $GeminiApiKey) {
    if (-not (Test-Path ".env")) {
        if ($GeminiApiKey) {
            @"
# Proxi Windows Agent Configuration
GEMINI_API_KEY=$GeminiApiKey
PROXI_AGENT_KEY=
"@ | Out-File -FilePath ".env" -Encoding UTF8
            Write-Host "✅ Created .env with GEMINI_API_KEY" -ForegroundColor Green
        } else {
            @"
# Proxi Windows Agent Configuration
# Get your API key from https://aistudio.google.com/apikey
GEMINI_API_KEY=your-api-key-here
PROXI_AGENT_KEY=
"@ | Out-File -FilePath ".env" -Encoding UTF8
            Write-Host "✅ Created .env template - EDIT THIS FILE to add your GEMINI_API_KEY" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  .env already exists, skipping" -ForegroundColor Gray
    }
} else {
    if (Test-Path ".env") {
        Write-Host "  .env exists" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️ No .env file - ground_and_click will not work without GEMINI_API_KEY" -ForegroundColor Yellow
        Write-Host "  Run with -CreateEnv to create one" -ForegroundColor Gray
    }
}

# Verify installation
Write-Host ""
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "  VERIFICATION" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan

Write-Host ""
Write-Host "Testing critical imports..." -ForegroundColor Yellow

$testScript = @"
import sys
errors = []
try:
    import pyautogui
    print('  ✅ pyautogui')
except ImportError as e:
    print(f'  ❌ pyautogui: {e}')
    errors.append('pyautogui')

try:
    from pywinauto import Desktop, Application
    print('  ✅ pywinauto')
except ImportError as e:
    print(f'  ❌ pywinauto: {e}')
    errors.append('pywinauto')

try:
    import cv2
    print('  ✅ opencv-python (cv2)')
except ImportError as e:
    print(f'  ❌ opencv-python: {e}')
    errors.append('opencv-python')

try:
    import google.generativeai
    print('  ✅ google-generativeai')
except ImportError as e:
    print(f'  ❌ google-generativeai: {e}')
    errors.append('google-generativeai')

try:
    import psutil
    print('  ✅ psutil')
except ImportError as e:
    print(f'  ❌ psutil: {e}')
    errors.append('psutil')

if errors:
    print(f'\n❌ {len(errors)} packages failed to import')
    sys.exit(1)
else:
    print('\n✅ All critical packages imported successfully!')
    sys.exit(0)
"@

python -c $testScript

Write-Host ""
if ($LASTEXITCODE -eq 0) {
    Write-Host "=" * 60 -ForegroundColor Green
    Write-Host "  SUCCESS! Windows agent dependencies are ready." -ForegroundColor Green
    Write-Host "=" * 60 -ForegroundColor Green
    Write-Host ""
    Write-Host "To start the agent:" -ForegroundColor White
    Write-Host "  .\venv\Scripts\Activate.ps1" -ForegroundColor Yellow
    Write-Host "  python -m uvicorn backend.agent_server:app --host 0.0.0.0 --port 8081" -ForegroundColor Yellow
} else {
    Write-Host "=" * 60 -ForegroundColor Red
    Write-Host "  SOME PACKAGES FAILED - Review errors above" -ForegroundColor Red
    Write-Host "=" * 60 -ForegroundColor Red
}
