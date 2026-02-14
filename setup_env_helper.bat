@echo off
chcp 65001 >nul
echo ========================================
echo   环境变量设置辅助工具
echo ========================================
echo.
echo 此工具用于解决新电脑首次配置时不生效的问题。
echo.

REM 检查 Python 环境
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python
    pause
    exit /b 1
)

REM 检查管理员权限
net session >nul 2>&1
if errorlevel 1 (
    echo [提示] 建议以管理员权限运行此脚本，以确保能设置系统环境变量
    echo.
    set /p continue="是否继续? (Y/N): "
    if /i not "%continue%"=="Y" (
        exit /b 1
    )
)

REM 运行环境变量设置脚本
python "%~dp0set_env_helper.py"

if errorlevel 1 (
    echo.
    echo [错误] 设置失败，请查看上方错误信息
) else (
    echo.
    echo [成功] 环境变量设置完成
    echo.
    echo 重要提示：
    echo 1. 请关闭当前终端窗口
    echo 2. 重新打开终端后，环境变量才会生效
    echo 3. 之后可以正常使用 claude 或其他 CLI 工具
)

echo.
pause
