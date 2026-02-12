@echo off
chcp 65001 >nul
echo ========================================
echo   AI 模型切换器 — 打包脚本
echo ========================================
echo.

REM 激活 conda 环境
call conda activate volleyball
if errorlevel 1 (
    echo [错误] 无法激活 conda 环境 volleyball
    pause
    exit /b 1
)

REM 检查 pyinstaller
pyinstaller --version >nul 2>&1
if errorlevel 1 (
    echo [提示] 正在安装 PyInstaller...
    pip install pyinstaller
)

REM 清理旧的构建产物
echo [1/3] 清理旧构建...
if exist "build" rmdir /s /q "build"
if exist "dist\AI模型切换器" rmdir /s /q "dist\AI模型切换器"

REM 执行打包
echo [2/3] 正在打包...
pyinstaller app.spec --noconfirm

if errorlevel 1 (
    echo.
    echo [错误] 打包失败，请检查上方错误信息
    pause
    exit /b 1
)

REM 生成安装包
echo [3/4] 正在生成安装包...

set "ISCC="
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist "C:\Program Files\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"
if exist "E:\software\Inno Setup 6\ISCC.exe" set "ISCC=E:\software\Inno Setup 6\ISCC.exe"

if defined ISCC (
    "%ISCC%" installer.iss
    if errorlevel 1 (
        echo [警告] 安装包生成失败，但 PyInstaller 打包已完成
    ) else (
        echo [√] 安装包已生成
    )
) else (
    echo [跳过] 未检测到 Inno Setup 6，跳过安装包生成
    echo        下载地址: https://jrsoftware.org/isdl.php
    echo        安装后重新运行此脚本即可生成安装包
)

REM 完成
echo.
echo ========================================
echo   打包完成！
echo ========================================
echo.
echo  [绿色版]  dist\AI模型切换器\AI模型切换器.exe
if defined ISCC echo  [安装包]  installer_output\CodePivot_Setup_1.0.0.exe
echo.
echo  注意: config.json 会在首次运行时自动生成
echo.
pause
