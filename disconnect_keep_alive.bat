
@echo off
setlocal
echo ==================================================
echo      PROXI GHOST OPERATOR - SESSION KEEPER
echo ==================================================
echo.
echo This will disconnect your RDP session immediately.
echo The session will remain ACTIVE and UNLOCKED on the server.
echo.

:: Get the current user's Session ID
for /f "tokens=3" %%a in ('query user %USERNAME% ^| findstr /i %USERNAME%') do (
    set SESSION_ID=%%a
)

if "%SESSION_ID%"=="" (
    echo [ERROR] Could not find Session ID for user %USERNAME%.
    echo You might not be in a standard RDP session.
    pause
    exit /b
)

echo Found active Session ID: %SESSION_ID%
echo Disconnecting in 3 seconds...
timeout /t 3 /nobreak >nul

:: Disconnect and attach to console (Unlocks the GUI)
tscon %SESSION_ID% /dest:console

echo.
echo Done. If you see this, the session was not redirected.
pause

