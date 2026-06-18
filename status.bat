@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo === RS-Autopilot Service Status ===

netstat -ano 2>nul | findstr /C:"LISTENING" | findstr /C:":5000 " >nul
if %ERRORLEVEL%==0 (
    echo   Backend:  RUNNING  http://localhost:5000
) else (
    echo   Backend:  STOPPED
)

netstat -ano 2>nul | findstr /C:"LISTENING" | findstr /C:":5173 " >nul
if %ERRORLEVEL%==0 (
    echo   Frontend: RUNNING  http://localhost:5173
) else (
    echo   Frontend: STOPPED
)

if exist logs\runtime.log (
    for %%s in (logs\runtime.log) do echo   Log file: %%~zs bytes
) else (
    echo   Log file: none
)
