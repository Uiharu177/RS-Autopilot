@echo off
setlocal enabledelayedexpansion
title RS-Autopilot 更新脚本
cd /d "%~dp0"

echo === RS-Autopilot 一键更新 ===
echo.

rem === 检测 Python（与 start.bat 逻辑一致）===
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
    pause
    exit /b 1
)

rem 验证 Python 能正常运行（排除 Microsoft Store 占位符）
%PYTHON_EXE% -c "import sys; sys.exit(0)" >nul 2>&1
if !ERRORLEVEL! neq 0 (
    echo [!!] Python 找到了但无法运行（可能是 Microsoft Store 占位符）
    echo [..] 请在 Windows 设置 ^> 应用 ^> 高级应用设置 ^> 应用执行别名中
    echo [..] 关闭 python / python3 的开关，然后重新运行 update.bat
    echo [..] 或从 https://www.python.org/ 重新安装并勾选 "Add Python to PATH"
    pause
    exit /b 1
)

rem === 步骤 1/10：停止正在运行的服务 ===
echo [..] 步骤 1/10 - 正在停止服务...
if exist stop.bat (
    call stop.bat
    if !ERRORLEVEL! neq 0 (
        echo [!!] stop.bat 执行失败，终止更新
        pause
        exit /b 1
    )
) else (
    echo [WARN] 未找到 stop.bat，跳过停止服务
)
echo.

rem === 步骤 2/10：显示当前版本 ===
echo [..] 步骤 2/10 - 当前版本：
set CURRENT_VERSION=
for /f "delims=" %%v in ('%PYTHON_EXE% -c "from version import __version__; print(__version__)" 2^>nul') do set CURRENT_VERSION=%%v
if not defined CURRENT_VERSION (
    echo [WARN] 无法从 version.py 读取版本
    set CURRENT_VERSION=unknown
)
echo     !CURRENT_VERSION!
echo.

rem === 步骤 3/10：检查 Git 远程仓库 ===
echo [..] 步骤 3/10 - 检查 Git 远程仓库...
where git >nul 2>&1
if !ERRORLEVEL! neq 0 (
    echo [!!] 未找到 git，请从 https://git-scm.com/ 安装 Git
    pause
    exit /b 1
)
set HAS_REMOTE=0
for /f "delims=" %%r in ('git remote 2^>nul') do set HAS_REMOTE=1
if "!HAS_REMOTE!"=="0" (
    echo [!!] 未配置 Git 远程仓库，无法拉取更新
    echo [..] 请运行：git remote add origin https://github.com/Uiharu177/RS-Autopilot.git
    echo [..] 然后重新运行 update.bat
    pause
    exit /b 1
)
echo [OK] Git 远程仓库已配置
echo.

rem === 步骤 4/10：暂存本地改动 ===
echo [..] 步骤 4/10 - 暂存本地改动（git stash）...
set STASHED=0
set HAS_CHANGES=0
for /f "delims=" %%s in ('git status --porcelain 2^>nul') do set HAS_CHANGES=1
if "!HAS_CHANGES!"=="1" (
    git stash push -u -m "update.bat auto-stash %date% %time%" >nul 2>nul
    set STASH_RESULT=!ERRORLEVEL!
    if !STASH_RESULT! equ 0 (
        echo [OK] 本地改动已暂存
        set STASHED=1
    ) else (
        echo [!!] git stash 失败，终止更新
        pause
        exit /b 1
    )
) else (
    echo [..] 没有本地改动，跳过暂存
)
echo.

rem === 步骤 5/10：拉取最新代码 ===
echo [..] 步骤 5/10 - 拉取最新代码（git pull --rebase）...
git pull --rebase >nul 2>&1
set PULL_RESULT=!ERRORLEVEL!
if !PULL_RESULT! neq 0 (
    echo [!!] git pull --rebase 失败（错误码 !PULL_RESULT!）
    if "!STASHED!"=="1" (
        echo [..] 你的本地改动已保存在 git stash 中
        echo [..] 解决冲突后运行：git stash pop
    )
    echo [..] 请手动解决冲突后重新运行 update.bat
    pause
    exit /b 1
)
echo [OK] 代码已更新到最新版本
echo.

rem === 步骤 6/10：恢复本地改动 ===
if "!STASHED!"=="1" (
    echo [..] 步骤 6/10 - 恢复本地改动（git stash pop）...
    git stash pop >nul 2>&1
    set POP_RESULT=!ERRORLEVEL!
    if !POP_RESULT! neq 0 (
        echo [WARN] git stash pop 出现冲突！
        echo [..] 你的本地改动与拉取的代码存在冲突
        echo [..] 请手动解决冲突后执行：
        echo     git add ^<已解决的文件^>
        echo     git stash drop
        pause
        exit /b 1
    ) else (
        echo [OK] 本地改动已恢复
    )
) else (
    echo [..] 步骤 6/10 - 没需要恢复的改动，跳过
)
echo.

rem === 步骤 7/10：更新 Python 依赖 ===
echo [..] 步骤 7/10 - 更新 Python 依赖...
%PYTHON_EXE% -m pip install -r requirements.txt
if !ERRORLEVEL! neq 0 (
    echo [!!] pip install 失败，请查看上方错误信息
    pause
    exit /b 1
)
echo [OK] Python 依赖已更新
echo.

rem === 步骤 8/10：构建前端 ===
echo [..] 步骤 8/10 - 构建前端...
if exist web\package.json (
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
    echo [..] 未找到 web\package.json，跳过前端构建
)
echo.

rem === 步骤 9/10：显示新版本 ===
echo [..] 步骤 9/10 - 更新后版本：
set NEW_VERSION=
for /f "delims=" %%v in ('%PYTHON_EXE% -c "from version import __version__; print(__version__)" 2^>nul') do set NEW_VERSION=%%v
if not defined NEW_VERSION set NEW_VERSION=unknown
echo     !NEW_VERSION!
if "!NEW_VERSION!"=="unknown" (
    echo [WARN] 无法从 version.py 读取新版本
) else if "!CURRENT_VERSION!"=="!NEW_VERSION!" (
    echo [..] 版本未变化（!CURRENT_VERSION!）
) else (
    echo [OK] 已更新：!CURRENT_VERSION! -^> !NEW_VERSION!
)
echo.

rem === 步骤 10/10：提示启动 ===
echo ========================================
echo   更新完成！
echo   请运行 start.bat 启动服务
echo ========================================
echo.
echo Press any key to continue . . .
pause >nul
endlocal
