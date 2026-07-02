@echo off
chcp 65001 >nul
title RS-Autopilot

cd /d "%~dp0"

rem === Find Python ===
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    where python3 >nul 2>&1
    if %ERRORLEVEL% neq 0 (
        echo [!!] Python not found in PATH. Please install Python 3.11 or 3.12.
        pause
        exit /b 1
    )
    set PYTHON_EXE=python3
) else (
    set PYTHON_EXE=python
)

if not exist logs mkdir logs

echo [..] Stopping stale servers...
rem Kill our own backend/frontend processes by specific window title + executable name
taskkill /F /IM python.exe   /FI "WINDOWTITLE eq RS-Autopilot-Backend" >nul 2>&1
taskkill /F /IM python3.exe  /FI "WINDOWTITLE eq RS-Autopilot-Backend" >nul 2>&1
taskkill /F /IM node.exe     /FI "WINDOWTITLE eq RS-Autopilot-Frontend" >nul 2>&1
rem Cleanup port bindings -- only kill if the process is Python/Node
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr /C:":15177 " ^| findstr "LISTENING"') do call :kill_port %%a 15177 python backend
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr /C:":5173 " ^| findstr "LISTENING"') do call :kill_port %%a 5173 node frontend
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
timeout /t 2 /nobreak >nul

if exist web\node_modules\.vite (
    echo [..] Clearing Vite cache...
    rmdir /s /q web\node_modules\.vite
)

if exist web\package.json (
    echo [..] Installing frontend dependencies...
    call web\node_modules\.bin\vite.cmd --version >nul 2>&1
    if %ERRORLEVEL% neq 0 (
        echo [..] npm install...
        pushd web
        call npm install
        popd
    )

    echo [..] Building frontend...
    pushd web
    call npm run build
    popd
)

echo [..] Starting backend...
start "RS-Autopilot-Backend" /B "%PYTHON_EXE%" cli.py serve > logs\backend.log 2>&1
echo [OK] Backend starting at http://localhost:15177

echo.
echo   RS-Autopilot is running
echo   Open:  http://localhost:15177
echo.
echo   stop.bat   - Stop backend and frontend
echo   status.bat - Show status

echo.
echo [..] Opening browser...
timeout /t 3 /nobreak >nul
start "" http://127.0.0.1:15177/#/
