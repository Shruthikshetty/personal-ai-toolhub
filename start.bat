@echo off
TITLE Custom AI API Server
cd /d "%~dp0"

echo ========================================
echo   Activating Virtual Environment...
echo ========================================

if not exist venv (
    echo [ERROR] Virtual environment "venv" not found in %CD%
    echo Please create it first using: python -m venv venv
    pause
    exit /b
)

call venv\Scripts\activate

echo ========================================
echo   Starting Python App (run.py)...
echo ========================================

python run.py

echo.
echo ========================================
echo   Server has stopped.
echo ========================================
pause
