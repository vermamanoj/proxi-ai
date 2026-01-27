@echo off
echo ============================================
echo   Proxi Agent - Windows Desktop Automation
echo ============================================
echo.

REM Check if venv exists
if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found.
    echo Run: python -m venv venv
    echo Then: pip install -r backend/requirements.txt
    pause
    exit /b 1
)

REM Activate virtual environment
call venv\Scripts\activate.bat
echo Virtual environment activated.

REM Check for .env file
if not exist ".env" (
    echo [WARNING] No .env file found. Creating default...
    echo AGENT_NAME=windows-agent> .env
    echo CORE_URL=http://localhost:4000>> .env
    echo Created .env with defaults. Edit as needed.
)

echo.
echo Starting Proxi Agent on port 8081...
echo Press Ctrl+C to stop.
echo.

python -m uvicorn backend.agent_server:app --host 0.0.0.0 --port 8081 --reload

pause
