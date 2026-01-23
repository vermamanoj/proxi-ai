
@echo off
:: This script disconnects the current RDP session but keeps it unlocked 
:: and rendering on the server's console.
:: Allows Proxi's Vision/Click tools to work after you leave.

echo ==================================================
echo      PROXI GHOST OPERATOR - SESSION KEEPER
echo ==================================================
echo.
echo This will disconnect your RDP session immediately.
echo The session will remain ACTIVE and UNLOCKED on the server.
echo.
pause
tscon %sessionname% /dest:console
