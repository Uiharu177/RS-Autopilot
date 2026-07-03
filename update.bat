@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title RS-Autopilot Update

cd /d "%~dp0"

echo === RS-Autopilot Update Script ===
echo.

rem ---- Step 0: Stop running services ----
echo [..] Step 0/4 - Stopping running services...
call stop.bat
echo.

rem ---- Step 1: Git pull ----
echo [..] Step 1/4 - Pulling latest code from git...
where git >nul 2>&1
if !ERRORLEVEL! neq 0 (
    echo [!!] git not found in PATH. Skipping pull.
    echo [..] Manually run: git pull
) else (
    rem Check for local changes
    git diff --quiet 2>nul
    if !ERRORLEVEL! neq 0 (
        echo [..] Local changes detected, stashing...
        git stash push -m "update.bat auto-stash %date% %time%"
    )
    git pull --rebase
    if !ERRORLEVEL! neq 0 (
        echo [!!] git pull failed. Resolve conflicts manually, then re-run.
        pause
        exit /b 1
    )
    echo [OK] Code updated.
)
echo.

rem ---- Step 2: Update Python dependencies ----
echo [..] Step 2/4 - Updating Python dependencies...
pip install -r requirements.txt
if !ERRORLEVEL! neq 0 (
    echo [!!] pip install failed. Check the error above.
    pause
    exit /b 1
)
echo [OK] Python dependencies updated.
echo.

rem ---- Step 3: Update frontend ----
echo [..] Step 3/4 - Installing frontend dependencies...
if exist web\package.json (
    pushd web
    call npm install
    if !ERRORLEVEL! neq 0 (
        popd
        echo [!!] npm install failed.
        pause
        exit /b 1
    )
    echo [..] Building frontend...
    call npm run build
    if !ERRORLEVEL! neq 0 (
        popd
        echo [!!] npm run build failed.
        pause
        exit /b 1
    )
    popd
    echo [OK] Frontend updated and built.
) else (
    echo [..] web\package.json not found, skipping frontend.
)
echo.

rem ---- Step 4: Done ----
echo ========================================
echo   Update complete!
echo   Run start.bat to restart the service.
echo ========================================
echo.
pause
