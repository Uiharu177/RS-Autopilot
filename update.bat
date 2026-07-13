@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title RS-Autopilot Update
cd /d "%~dp0"

echo === RS-Autopilot Update Script ===
echo.

rem === Python detection (same as start.bat) ===
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
    pause
    exit /b 1
)

rem Verify the resolved python actually runs a real interpreter (not the Store stub).
%PYTHON_EXE% -c "import sys; sys.exit(0)" >nul 2>&1
if !ERRORLEVEL! neq 0 (
    echo [!!] Python was found but failed to run ^(maybe the Microsoft Store stub^).
    echo [..] Disable the "python" app execution alias in
    echo [..] Windows Settings ^> Apps ^> Advanced app settings ^> App execution aliases,
    echo [..] then re-run update.bat, or install Python from https://www.python.org/
    pause
    exit /b 1
)

rem === Step 1: Stop running services ===
echo [..] Step 1/10 - Stopping running services...
if exist stop.bat (
    call stop.bat
    if !ERRORLEVEL! neq 0 (
        echo [!!] stop.bat failed. Aborting update.
        pause
        exit /b 1
    )
) else (
    echo [WARN] stop.bat not found, continuing without stopping services.
)
echo.

rem === Step 2: Show current version ===
echo [..] Step 2/10 - Current version:
set CURRENT_VERSION=
for /f "delims=" %%v in ('%PYTHON_EXE% -c "from version import __version__; print(__version__)" 2^>nul') do set CURRENT_VERSION=%%v
if not defined CURRENT_VERSION (
    echo [WARN] Could not read version from version.py
    set CURRENT_VERSION=unknown
)
echo     !CURRENT_VERSION!
echo.

rem === Step 3: Check git remote ===
echo [..] Step 3/10 - Checking git remote...
where git >nul 2>&1
if !ERRORLEVEL! neq 0 (
    echo [!!] git not found in PATH. Please install Git from https://git-scm.com/
    pause
    exit /b 1
)
set HAS_REMOTE=0
for /f "delims=" %%r in ('git remote 2^>nul') do set HAS_REMOTE=1
if "!HAS_REMOTE!"=="0" (
    echo [!!] No git remote configured. Cannot pull updates.
    echo [..] To configure a remote, run:
    echo     git remote add origin https://github.com/Uiharu177/RS-Autopilot.git
    echo [..] Then re-run update.bat
    pause
    exit /b 1
)
echo [OK] Git remote configured.
echo.

rem === Step 4: git stash (save local changes) ===
echo [..] Step 4/10 - Saving local changes (git stash)...
set STASHED=0
set HAS_CHANGES=0
for /f "delims=" %%s in ('git status --porcelain 2^>nul') do set HAS_CHANGES=1
if "!HAS_CHANGES!"=="1" (
    git stash push -u -m "update.bat auto-stash %date% %time%"
    if !ERRORLEVEL! equ 0 (
        echo [OK] Local changes stashed.
        set STASHED=1
    ) else (
        echo [!!] git stash failed. Aborting.
        pause
        exit /b 1
    )
) else (
    echo [..] No local changes to stash.
)
echo.

rem === Step 5: git pull --rebase ===
echo [..] Step 5/10 - Pulling latest code (git pull --rebase)...
git pull --rebase
if !ERRORLEVEL! neq 0 (
    echo [!!] git pull --rebase failed.
    if "!STASHED!"=="1" (
        echo [..] Your local changes are saved in git stash.
        echo [..] Run: git stash pop  (after resolving conflicts)
    )
    echo [..] Resolve conflicts manually, then re-run update.bat.
    pause
    exit /b 1
)
echo [OK] Code updated.
echo.

rem === Step 6: git stash pop (restore local changes) ===
if "!STASHED!"=="1" (
    echo [..] Step 6/10 - Restoring local changes (git stash pop)...
    git stash pop
    if !ERRORLEVEL! neq 0 (
        echo [WARN] git stash pop reported conflicts!
        echo [..] Your local changes conflicted with the pulled code.
        echo [..] Resolve the conflicts manually, then:
        echo     git add ^<resolved-files^>
        echo     git stash drop
        pause
        exit /b 1
    ) else (
        echo [OK] Local changes restored.
    )
) else (
    echo [..] Step 6/10 - No stash to restore, skipping.
)
echo.

rem === Step 7: pip install -r requirements.txt ===
echo [..] Step 7/10 - Updating Python dependencies...
%PYTHON_EXE% -m pip install -r requirements.txt
if !ERRORLEVEL! neq 0 (
    echo [!!] pip install failed. Check the error above.
    pause
    exit /b 1
)
echo [OK] Python dependencies updated.
echo.

rem === Step 8: cd web && npm install && npm run build && cd .. ===
echo [..] Step 8/10 - Building frontend...
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

rem === Step 9: Show new version ===
echo [..] Step 9/10 - New version:
set NEW_VERSION=
for /f "delims=" %%v in ('%PYTHON_EXE% -c "from version import __version__; print(__version__)" 2^>nul') do set NEW_VERSION=%%v
if not defined NEW_VERSION set NEW_VERSION=unknown
echo     !NEW_VERSION!
if "!NEW_VERSION!"=="unknown" (
    echo [WARN] Could not read new version from version.py
) else if "!CURRENT_VERSION!"=="!NEW_VERSION!" (
    echo [..] Version unchanged (!CURRENT_VERSION!).
) else (
    echo [OK] Updated: !CURRENT_VERSION! -^> !NEW_VERSION!
)
echo.

rem === Step 10: Prompt to run start.bat ===
echo ========================================
echo   Update complete!
echo   Run start.bat to start the service.
echo ========================================
echo.
pause
endlocal
