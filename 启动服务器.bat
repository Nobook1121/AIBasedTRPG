@echo off
setlocal
cd /d "%~dp0"
call "%~dp0start_server.bat" %*
exit /b %ERRORLEVEL%
