# Proxi Windows Agent Diagnostic Script
# Run this on the Windows agent machine to verify dependencies
# Usage: .\scripts\diagnose-windows-agent.ps1

Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "  PROXI WINDOWS AGENT DIAGNOSTICS" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""

$errors = @()
$warnings = @()

# 1. Check Python
Write-Host "[1/7] Checking Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    if ($pythonVersion -match "Python 3\.1[012]") {
        Write-Host "  ✅ $pythonVersion" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️ $pythonVersion (Recommended: Python 3.10+)" -ForegroundColor Yellow
        $warnings += "Python version may be outdated"
    }
} catch {
    Write-Host "  ❌ Python not found in PATH" -ForegroundColor Red
    $errors += "Python not installed or not in PATH"
}

# 2. Check Virtual Environment
Write-Host "[2/7] Checking Virtual Environment..." -ForegroundColor Yellow
$venvPath = ".\venv\Scripts\python.exe"
if (Test-Path $venvPath) {
    Write-Host "  ✅ venv found at $venvPath" -ForegroundColor Green
    $pythonExe = $venvPath
} else {
    Write-Host "  ⚠️ No venv found - using system Python" -ForegroundColor Yellow
    $warnings += "No virtual environment - using system Python"
    $pythonExe = "python"
}

# 3. Check Critical Dependencies
Write-Host "[3/7] Checking Critical Dependencies..." -ForegroundColor Yellow

$criticalPackages = @(
    @{Name="pyautogui"; Required=$true; Purpose="Mouse/keyboard automation"},
    @{Name="pywinauto"; Required=$true; Purpose="Window management, UI tree"},
    @{Name="opencv-python"; Required=$true; Purpose="Screenshot processing"},
    @{Name="numpy"; Required=$true; Purpose="Image array handling"},
    @{Name="pyperclip"; Required=$true; Purpose="Clipboard operations"},
    @{Name="google-generativeai"; Required=$true; Purpose="Visual grounding (ground_and_click)"},
    @{Name="python-dotenv"; Required=$false; Purpose=".env file loading"},
    @{Name="fastapi"; Required=$true; Purpose="Agent HTTP server"},
    @{Name="uvicorn"; Required=$true; Purpose="ASGI server"},
    @{Name="psutil"; Required=$true; Purpose="System metrics"}
)

foreach ($pkg in $criticalPackages) {
    $result = & $pythonExe -c "import importlib.util; print('OK' if importlib.util.find_spec('$($pkg.Name.Replace('-','_').Replace('opencv-python','cv2').Replace('google-generativeai','google.generativeai').Replace('python-dotenv','dotenv'))') else 'MISSING')" 2>&1
    if ($result -eq "OK") {
        Write-Host "  ✅ $($pkg.Name) - $($pkg.Purpose)" -ForegroundColor Green
    } else {
        if ($pkg.Required) {
            Write-Host "  ❌ $($pkg.Name) MISSING - $($pkg.Purpose)" -ForegroundColor Red
            $errors += "$($pkg.Name) not installed"
        } else {
            Write-Host "  ⚠️ $($pkg.Name) missing (optional) - $($pkg.Purpose)" -ForegroundColor Yellow
            $warnings += "$($pkg.Name) not installed (optional)"
        }
    }
}

# 4. Check pywinauto specifically (the main culprit)
Write-Host "[4/7] Testing pywinauto Import..." -ForegroundColor Yellow
$pywinautoTest = & $pythonExe -c @"
try:
    from pywinauto import Desktop, Application
    import ctypes
    print('OK')
except ImportError as e:
    print(f'IMPORT_ERROR:{e}')
except Exception as e:
    print(f'ERROR:{e}')
"@ 2>&1

if ($pywinautoTest -eq "OK") {
    Write-Host "  ✅ pywinauto imports successfully" -ForegroundColor Green
} else {
    Write-Host "  ❌ pywinauto import failed: $pywinautoTest" -ForegroundColor Red
    $errors += "pywinauto import failed: $pywinautoTest"
}

# 5. Check Environment Variables
Write-Host "[5/7] Checking Environment Variables..." -ForegroundColor Yellow

# Check for .env file
$envFile = ".\.env"
if (Test-Path $envFile) {
    Write-Host "  ✅ .env file found" -ForegroundColor Green
    
    # Check for GEMINI_API_KEY in .env
    $envContent = Get-Content $envFile -Raw
    if ($envContent -match "GEMINI_API_KEY=\S+") {
        Write-Host "  ✅ GEMINI_API_KEY present in .env" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️ GEMINI_API_KEY not found in .env (needed for ground_and_click)" -ForegroundColor Yellow
        $warnings += "GEMINI_API_KEY not in .env"
    }
} else {
    Write-Host "  ⚠️ No .env file found" -ForegroundColor Yellow
    $warnings += "No .env file"
}

# Check system environment
if ($env:GEMINI_API_KEY) {
    Write-Host "  ✅ GEMINI_API_KEY set in environment" -ForegroundColor Green
} else {
    Write-Host "  ⚠️ GEMINI_API_KEY not in system environment" -ForegroundColor Yellow
}

# 6. Test Agent Health Endpoint
Write-Host "[6/7] Testing Agent Health Endpoint..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8081/health" -Method GET -TimeoutSec 5 -ErrorAction Stop
    Write-Host "  ✅ Agent responding on :8081" -ForegroundColor Green
    Write-Host "     Platform: $($health.platform)" -ForegroundColor Gray
    Write-Host "     Status: $($health.status)" -ForegroundColor Gray
} catch {
    Write-Host "  ⚠️ Agent not responding on :8081 (may not be running)" -ForegroundColor Yellow
    $warnings += "Agent not responding on port 8081"
}

# 7. Test Window Enumeration
Write-Host "[7/7] Testing Window Enumeration (list_windows)..." -ForegroundColor Yellow
$windowTest = & $pythonExe -c @"
import platform
USE_ACCESSIBILITY = False
if platform.system() == 'Windows':
    try:
        import ctypes
        from pywinauto import Desktop
        USE_ACCESSIBILITY = True
        desktop = Desktop(backend='uia')
        windows = desktop.windows(visible_only=True)
        titles = [w.window_text() for w in windows[:5] if w.window_text()]
        print(f'OK:{len(windows)} windows, samples: {titles}')
    except ImportError as e:
        print(f'IMPORT_ERROR:{e}')
    except Exception as e:
        print(f'ERROR:{e}')
else:
    print('NOT_WINDOWS')
"@ 2>&1

if ($windowTest -match "^OK:") {
    Write-Host "  ✅ Window enumeration works: $windowTest" -ForegroundColor Green
} else {
    Write-Host "  ❌ Window enumeration failed: $windowTest" -ForegroundColor Red
    $errors += "Window enumeration failed"
}

# Summary
Write-Host ""
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "  DIAGNOSTIC SUMMARY" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan

if ($errors.Count -eq 0) {
    Write-Host "✅ All critical checks passed!" -ForegroundColor Green
} else {
    Write-Host "❌ $($errors.Count) CRITICAL ERRORS:" -ForegroundColor Red
    foreach ($err in $errors) {
        Write-Host "   - $err" -ForegroundColor Red
    }
}

if ($warnings.Count -gt 0) {
    Write-Host "⚠️ $($warnings.Count) Warnings:" -ForegroundColor Yellow
    foreach ($warn in $warnings) {
        Write-Host "   - $warn" -ForegroundColor Yellow
    }
}

# Fix Instructions
if ($errors.Count -gt 0) {
    Write-Host ""
    Write-Host "=" * 60 -ForegroundColor Cyan
    Write-Host "  FIX INSTRUCTIONS" -ForegroundColor Cyan
    Write-Host "=" * 60 -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Run the following to fix missing dependencies:" -ForegroundColor White
    Write-Host ""
    Write-Host "# Activate venv first" -ForegroundColor Gray
    Write-Host ".\venv\Scripts\Activate.ps1" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "# Install all required packages" -ForegroundColor Gray
    Write-Host "pip install pyautogui pywinauto opencv-python numpy pyperclip google-generativeai python-dotenv fastapi uvicorn psutil pywin32" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "# Create .env file with API key" -ForegroundColor Gray
    Write-Host '@"' -ForegroundColor Yellow
    Write-Host "GEMINI_API_KEY=your-api-key-here" -ForegroundColor Yellow
    Write-Host '"@ | Out-File -FilePath .env -Encoding UTF8' -ForegroundColor Yellow
    Write-Host ""
    Write-Host "# Restart the agent" -ForegroundColor Gray
    Write-Host "python -m uvicorn backend.agent_server:app --host 0.0.0.0 --port 8081" -ForegroundColor Yellow
}

Write-Host ""
