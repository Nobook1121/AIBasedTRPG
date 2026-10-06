@echo off
REM ============================================================
REM  The Veil - Windows launcher
REM
REM  Usage:
REM    start.cmd            start with the configured port
REM    start.cmd 8090       start with a specific port
REM
REM  Prefers the Python inside .venv when present, otherwise
REM  falls back to python on PATH.
REM
REM  Double-click friendly: no PowerShell execution policy needed.
REM ============================================================
setlocal

cd /d "%~dp0"

REM Keep Python's UTF-8 output readable in the Windows console
set "PYTHONIOENCODING=utf-8"
chcp 65001 >nul 2>&1
title The Veil

set "PYTHON=%~dp0.venv\Scripts\python.exe"
if not exist "%PYTHON%" set "PYTHON=python"

"%PYTHON%" --version >nul 2>&1
if errorlevel 1 (
  echo.
  echo [The Veil] Python not found.
  echo            Install Python 3.11+ from https://www.python.org/downloads/
  echo            and tick "Add python.exe to PATH" during setup.
  echo.
  pause
  exit /b 1
)

echo [The Veil] Starting server (Python: %PYTHON%) ...
"%PYTHON%" server.py %*
set "EXITCODE=%ERRORLEVEL%"

if not "%EXITCODE%"=="0" (
  echo.
  echo [The Veil] Server exited with code %EXITCODE%.
  pause
)
exit /b %EXITCODE%