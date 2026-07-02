@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo [..] Stopping backend...
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr /C:":15177 " ^| findstr "LISTENING"') do call :kill_port %%a 15177 python Backend
echo [..] Stopping frontend...
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr /C:":5173 " ^| findstr "LISTENING"') do call :kill_port %%a 5173 node Frontend
goto :after_kill_port

:kill_port
tasklist /FI "PID eq %1" /FO CSV /NH 2>nul | findstr /I "%3" >nul
if errorlevel 1 (
    echo [WARN] %4 PID %1 is not a %3 process - skipping
) else (
    taskkill /F /PID %1 >nul 2>&1
    echo [OK] %4 process %1 stopped
)
exit /b

:after_kill_port
echo [OK] RS-Autopilot stopped
