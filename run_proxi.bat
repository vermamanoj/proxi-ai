@echo off
echo Starting Proxi Ghost Operator (Virtual Env)...
cd /d %~dp0

:: Check if venv exists
if not exist venv\Scripts\activate.bat (
    echo [ERROR] Virtual Environment not found at %~dp0venv
    echo Please run "powershell -ExecutionPolicy Bypass -File setup_windows.ps1" first.
    pause
    exit /b
)

:: Activate and Run
call venv\Scripts\activate
echo Virtual Environment Activated.
echo Starting Uvicorn on Port 8080...
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8080 --reload
pause