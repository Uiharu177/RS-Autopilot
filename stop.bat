@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo [..] 正在停止服务...
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr /C:":15177 " ^| findstr "LISTENING"') do call :kill_port %%a 15177 python 后端
goto :after_kill_port

:kill_port
tasklist /FI "PID eq %1" /FO CSV /NH 2>nul | findstr /I "%3" >nul
if errorlevel 1 (
    echo [WARN] %4 PID %1 不是 %3 进程，跳过
) else (
    taskkill /F /PID %1 >nul 2>&1
    echo [OK] 已停止 %4 进程 %1
)
exit /b

:after_kill_port
echo [OK] RS-Autopilot 已停止
