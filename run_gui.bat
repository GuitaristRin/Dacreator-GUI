@echo off
chcp 65001 > nul
title DACreator 启动器

echo ========================================
echo        DACreator 成绩表生成工具
echo ========================================
echo.

REM 获取脚本所在目录
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM 检查 Python 是否安装
python --version > nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python 环境！
    echo.
    echo 请先安装 Python 3.7 或更高版本
    echo 下载地址：https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

REM 显示 Python 版本
for /f "tokens=*" %%i in ('python --version 2^>^&1') do set "PYTHON_VERSION=%%i"
echo [信息] 检测到 %PYTHON_VERSION%
echo.

REM 直接启动 GUI，让程序自己处理依赖检查
echo [信息] 正在启动 DACreator GUI...
echo.
python dacreator_gui.py

REM 如果程序异常退出，暂停以便查看错误信息
if errorlevel 1 (
    echo.
    echo [错误] 程序异常退出
    pause
)