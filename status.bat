@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo === RS-Autopilot Service Status ===

netstat -ano 2>nul | findstr /C:"LISTENING" | findstr /C:":15177 " >nul
if %ERRORLEVEL%==0 (
    echo   Backend:  RUNNING  http://localhost:15177
) else (
    echo   Backend:  STOPPED
)

echo   Frontend: served by Backend ^(open http://localhost:15177^)

if exist logs\runtime.log (
    for %%s in (logs\runtime.log) do echo   Log file: %%~zs bytes
) else (
    echo   Log file: none
)
