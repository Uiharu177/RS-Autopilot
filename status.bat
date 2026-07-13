@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo === RS-Autopilot 服务状态 ===

netstat -ano 2>nul | findstr /C:"LISTENING" | findstr /C:":15177 " >nul
if %ERRORLEVEL%==0 (
    echo   后端：运行中  http://localhost:15177
) else (
    echo   后端：已停止
)

echo   前端：由后端提供 ^(打开 http://localhost:15177^)

if exist logs\runtime.log (
    for %%s in (logs\runtime.log) do echo   日志文件：%%~zs 字节
) else (
    echo   日志文件：无
)
