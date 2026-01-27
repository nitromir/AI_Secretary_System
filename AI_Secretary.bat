@echo off
title AI Secretary System
cd /d "%~dp0"

echo ========================================
echo   AI Secretary System - Starting...
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Please install Python 3.10+
    pause
    exit /b 1
)

REM Check if orchestrator is already running
netstat -an | findstr ":8002" >nul 2>&1
if not errorlevel 1 (
    echo [INFO] Orchestrator already running on port 8002
    goto :open_browser
)

REM Start orchestrator
echo [INFO] Starting orchestrator...
start "AI Secretary Orchestrator" cmd /c "python orchestrator.py"

REM Wait for startup
echo [INFO] Waiting for server to start...
timeout /t 5 /nobreak >nul

:open_browser
echo [INFO] Opening admin panel...
start http://localhost:8002/admin/

echo.
echo ========================================
echo   Admin Panel: http://localhost:8002/admin/
echo   Login: admin / admin
echo ========================================
echo.
echo Press any key to close this window...
pause >nul
