@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title RS-Autopilot

cd /d "%~dp0"

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
    echo [!!] 未找到 Python，请安装 Python 3.11 或 3.12
    echo [..] 安装时勾选 "Add Python to PATH"
    echo [..] 如果已安装，请在 Windows 设置 ^> 应用 ^> 高级应用设置 ^> 应用执行别名中
    echo [..] 关闭 python / python3 的开关
    pause
    exit /b 1
)

%PYTHON_EXE% -c "import sys; sys.exit(0)" >nul 2>&1
if !ERRORLEVEL! neq 0 (
    echo [!!] Python 找到了但无法运行（可能是 Microsoft Store 占位符）
    echo [..] 请在 Windows 设置 ^> 应用 ^> 高级应用设置 ^> 应用执行别名中
    echo [..] 关闭 python / python3 的开关，然后重新运行 start.bat
    echo [..] 或从 https://www.python.org/ 重新安装并勾选 "Add Python to PATH"
    pause
    exit /b 1
)

if not exist logs mkdir logs

echo [..] 正在停止残留进程...
taskkill /F /IM python.exe   /FI "WINDOWTITLE eq RS-Autopilot-Backend" >nul 2>&1
taskkill /F /IM python3.exe  /FI "WINDOWTITLE eq RS-Autopilot-Backend" >nul 2>&1
taskkill /F /IM py.exe       /FI "WINDOWTITLE eq RS-Autopilot-Backend" >nul 2>&1
taskkill /F /IM node.exe     /FI "WINDOWTITLE eq RS-Autopilot-Frontend" >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr /C:":15177 " ^| findstr "LISTENING"') do call :kill_port %%a 15177 python 后端
goto :after_kill_port

:kill_port
tasklist /FI "PID eq %1" /FO CSV /NH 2>nul | findstr /I "%3" >nul
if errorlevel 1 (
    echo [WARN] 端口 %2 被非 %3 进程占用 ^(PID %1^)，跳过
) else (
    taskkill /F /PID %1 >nul 2>&1
    echo [..] 已停止占用端口 %2 的 %4 ^(PID %1^)
)
exit /b

:after_kill_port
ping -n 3 127.0.0.1 >nul

if exist web\node_modules\.vite (
    echo [..] 清理 Vite 缓存...
    rmdir /s /q web\node_modules\.vite
)

if exist web\package.json (
    if not exist web\dist\index.html (
        echo [..] 首次启动，正在安装前端依赖...
        pushd web
        call npm install
        if !ERRORLEVEL! neq 0 (
            popd
            echo [!!] npm install 失败
            pause
            exit /b 1
        )
        echo [..] 正在构建前端...
        call npm run build
        if !ERRORLEVEL! neq 0 (
            popd
            echo [!!] npm run build 失败
            pause
            exit /b 1
        )
        popd
        echo [OK] 前端已构建完成
    ) else (
        echo [..] 前端已构建，跳过
    )
)

echo [..] 正在启动后端...
if exist logs\backend.log type nul > logs\backend.log
start "RS-Autopilot-Backend" /B %PYTHON_EXE% cli.py serve > logs\backend.log 2>&1

echo [..] 等待后端就绪（最多 30 秒）...
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
    echo [!!] 后端在 30 秒内未能启动
    echo [..] 端口 15177 未监听。常见原因：
    echo [..]   1. 缺少 Python 依赖 - 运行：pip install -r requirements.txt
    echo [..]   2. 端口 15177 被其他程序占用
    echo [..]   3. Python 是 Microsoft Store 占位符（关闭应用执行别名）
    echo.
    echo [..] logs\backend.log 最后 20 行：
    echo ----------------------------------------
    powershell -NoProfile -Command "Get-Content logs\backend.log -Tail 20 -Encoding utf8 2>$null"
    echo ----------------------------------------
    echo.
    echo [..] 完整日志：logs\backend.log
    pause
    exit /b 1
)

echo [OK] 后端已启动：http://localhost:15177
echo.
echo   RS-Autopilot 正在运行
echo   打开：http://localhost:15177
echo.
echo   stop.bat   - 停止后端
echo   status.bat - 查看状态
echo.

echo [..] 正在打开浏览器...
start "" http://127.0.0.1:15177/#/

echo.
echo   服务正在后台运行，关闭此窗口不影响服务
echo   如需停止服务，请运行 stop.bat
echo.
pause >nul
endlocal
