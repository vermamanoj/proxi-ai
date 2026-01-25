@echo off
echo Starting Proxi Ghost Operator (Virtual Env)...
cd %~dp0
call venv\Scripts\activate
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8080 --reload
pause