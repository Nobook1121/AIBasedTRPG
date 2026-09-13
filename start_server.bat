@echo off
setlocal
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
    echo Python 3 was not found on PATH.
    pause
    exit /b 1
)
echo Starting AIbased TRPG server...
python server.py %*
set "EXIT_CODE=%ERRORLEVEL%"
echo.
if not "%EXIT_CODE%"=="0" echo Server exited with code %EXIT_CODE%.
pause
exit /b %EXIT_CODE%
