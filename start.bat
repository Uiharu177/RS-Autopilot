@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title RS-Autopilot

cd /d "%~dp0"

rem === Find Python ===
rem Prefer the official "py" launcher, then python, then python3.
rem Also reject the Microsoft Store stub which launches the Store instead of running.
set PYTHON_EXE=

where py >nul 2>&1
if !ERRORLEVEL! equ 0 (
    set PYTHON_EXE=py -3
) else (
    where python >nul 2>&1
    if !ERRORLEVEL! equ 0 (
        set PYTHON_EXE=python
    ) else (
        where python3 >nul 2>&1
        if !ERRORLEVEL! equ 0 (
            set PYTHON_EXE=python3
        )
    )
)

if not defined PYTHON_EXE (
    echo [!!] Python not found in PATH. Please install Python 3.11 or 3.12
    echo [..] and tick "Add Python to PATH" during installation.
    echo [..] If you already installed it, also disable the "python" app execution
    echo [..] alias in Windows Settings ^> Apps ^> Advanced app settings ^> App execution aliases.
    pause
    exit /b 1
)

rem Verify the resolved python actually runs a real interpreter (not the Store stub).
%PYTHON_EXE% -c "import sys; sys.exit(0)" >nul 2>&1
if !ERRORLEVEL! neq 0 (
    echo [!!] Python was found but failed to run ^(maybe the Microsoft Store stub^).
    echo [..] Disable the "python" app execution alias in
    echo [..] Windows Settings ^> Apps ^> Advanced app settings ^> App execution aliases,
    echo [..] then re-run start.bat, or install Python from https://www.python.org/
    pause
    exit /b 1
)

if not exist logs mkdir logs

echo [..] Stopping stale servers...
rem Kill our own backend/frontend processes by specific window title + executable name
taskkill /F /IM python.exe   /FI "WINDOWTITLE eq RS-Autopilot-Backend" >nul 2>&1
taskkill /F /IM python3.exe  /FI "WINDOWTITLE eq RS-Autopilot-Backend" >nul 2>&1
taskkill /F /IM py.exe       /FI "WINDOWTITLE eq RS-Autopilot-Backend" >nul 2>&1
taskkill /F /IM node.exe     /FI "WINDOWTITLE eq RS-Autopilot-Frontend" >nul 2>&1
rem Cleanup port bindings -- only kill if the process is Python/Node
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr /C:":15177 " ^| findstr "LISTENING"') do call :kill_port %%a 15177 python backend
goto :after_kill_port

:kill_port
tasklist /FI "PID eq %1" /FO CSV /NH 2>nul | findstr /I "%3" >nul
if errorlevel 1 (
    echo [WARN] Port %2 occupied by non-%3 process ^(PID %1^), skipping
) else (
    taskkill /F /PID %1 >nul 2>&1
    echo [..] Stopped stale %4 on port %2 ^(PID %1^)
)
exit /b

:after_kill_port
ping -n 3 127.0.0.1 >nul

if exist web\node_modules\.vite (
    echo [..] Clearing Vite cache...
    rmdir /s /q web\node_modules\.vite
)

if exist web\package.json (
    echo [..] Installing frontend dependencies...
    pushd web
    call npm install
    popd

    echo [..] Building frontend...
    pushd web
    call npm run build
    popd
)

echo [..] Starting backend...
rem Truncate the old log so the readiness check only sees this run's output.
if exist logs\backend.log type nul > logs\backend.log
start "RS-Autopilot-Backend" /B %PYTHON_EXE% cli.py serve > logs\backend.log 2>&1

echo [..] Waiting for backend to be ready ^(up to 30s^)...
set READY=0
for /l %%i in (1,1,60) do (
    netstat -ano 2>nul | findstr /C:":15177 " | findstr "LISTENING" >nul
    if !ERRORLEVEL! equ 0 (
        set READY=1
        goto :ready
    )
    ping -n 2 127.0.0.1 >nul
)

:ready
if "!READY!"=="0" (
    echo.
    echo [!!] Backend failed to start within 30s.
    echo [..] Port 15177 is not listening. Common causes:
    echo [..]   1. Missing Python dependencies - run: pip install -r requirements.txt
    echo [..]   2. Port 15177 occupied by another program
    echo [..]   3. Python is the Microsoft Store stub ^(disable app execution alias^)
    echo.
    echo [..] Last lines of logs\backend.log:
    echo ----------------------------------------
    powershell -NoProfile -Command "Get-Content logs\backend.log -Tail 20 -Encoding utf8 2>$null"
    echo ----------------------------------------
    echo.
    echo [..] Full log: logs\backend.log
    pause
    exit /b 1
)

echo [OK] Backend is running at http://localhost:15177
echo.
echo   RS-Autopilot is running
echo   Open:  http://localhost:15177
echo.
echo   stop.bat   - Stop backend and frontend
echo   status.bat - Show status
echo.

echo [..] Opening browser...
start "" http://127.0.0.1:15177/#/

endlocal