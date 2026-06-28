@echo off
cd /d "%~dp0"
title resonance_ng

rem === System Python (with resonance_ng deps) ===
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    where python3 >nul 2>&1
    if %ERRORLEVEL% neq 0 (
        echo [!!] Python not found in PATH. Please install Python 3.12+
        pause
        exit /b 1
    )
    set PYTHON_EXE=python3
) else (
    set PYTHON_EXE=python
)

if not exist logs mkdir logs

echo [..] Stopping stale servers...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr /C:":5000 " ^| findstr /C:"LISTENING"') do call :kill_port %%a 5000 python backend
for /f "tokens=5" %%a in ('netstat -ano ^| findstr /C:":5173 " ^| findstr /C:"LISTENING"') do call :kill_port %%a 5173 node frontend
goto :after_kill_port

:kill_port
tasklist /FI "PID eq %1" /FO CSV /NH 2>nul | findstr /I "%3" >nul
if errorlevel 1 (
    echo [WARN] Port %2 occupied by non-%3 process ^(PID %1^), skipping
) else (
    taskkill /F /PID %1 >nul 2>&1
    echo [..] Stopped stale %4 on port %2
)
exit /b

:after_kill_port

if exist web\node_modules\.vite (
    echo [..] Clearing Vite cache...
    rmdir /s /q web\node_modules\.vite
)

echo [..] Starting backend...
start /B "" "%PYTHON_EXE%" cli.py serve
echo [OK] Backend starting at http://localhost:5000

if exist web\package.json (
    echo [..] Installing frontend dependencies...
    call web\node_modules\.bin\vite.cmd --version >nul 2>&1
    if %ERRORLEVEL% neq 0 (
        echo [..] npm install...
        cd /d web
        call npm install
        cd /d "%~dp0"
    )

    echo [..] Starting frontend dev server...
    start /B cmd /c "cd /d %~dp0web && npm run dev > ..\logs\vite.log 2>&1"
    echo [OK] Frontend starting at http://127.0.0.1:5173
)

echo.
echo   Open:  http://127.0.0.1:5173
echo.
echo   stop.bat   - Stop backend and frontend
echo   status.bat - Show status

echo.
echo [..] Opening browser...
timeout /t 3 /nobreak >nul
start "" http://127.0.0.1:5173/#/
