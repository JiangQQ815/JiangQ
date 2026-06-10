@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"

echo ================================================================
echo            ADB Device Tool
echo ================================================================
echo.

python main.py

if errorlevel 1 (
    echo.
    echo [ERROR] Failed to run. Please ensure Python 3.x is installed.
)

echo.
pause