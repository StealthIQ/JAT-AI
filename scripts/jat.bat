@echo off
title JAT-AI
echo.
echo  ========================================
echo   JAT-AI - Starting...
echo  ========================================
echo.

set ROOT=%~dp0..
set BACKEND_PORT=8000
set FRONTEND_PORT=3000

:: Check if .env exists
if not exist "%ROOT%\.env" (
    echo [ERROR] .env file not found. Copy .env.example and fill in your keys.
    pause
    exit /b 1
)

:: Install Python deps if needed
if not exist "%ROOT%\.cache\deps_installed" (
    echo [SETUP] Installing Python dependencies...
    pip install -e "%ROOT%" >nul 2>&1
    if not exist "%ROOT%\.cache" mkdir "%ROOT%\.cache"
    echo done > "%ROOT%\.cache\deps_installed"
)

:: Install frontend deps if needed
if not exist "%ROOT%\dashboard\node_modules" (
    echo [SETUP] Installing dashboard dependencies...
    cd /d "%ROOT%\dashboard"
    npm install >nul 2>&1
)

:: Start backend
echo [BACKEND] Starting FastAPI on port %BACKEND_PORT%...
cd /d "%ROOT%"
start /b "" python -m uvicorn api.server:app --port %BACKEND_PORT% --reload --app-dir src

:: Wait for backend to be ready
echo [BACKEND] Waiting for server...
:wait_backend
timeout /t 1 /nobreak >nul
curl -s http://localhost:%BACKEND_PORT%/api/setup >nul 2>&1
if errorlevel 1 goto wait_backend
echo [BACKEND] Ready on http://localhost:%BACKEND_PORT%

:: Start frontend
echo [FRONTEND] Starting Vite on port %FRONTEND_PORT%...
cd /d "%ROOT%\dashboard"
start /b "" npx vite --port %FRONTEND_PORT% >nul 2>&1

:: Wait for frontend
:wait_frontend
timeout /t 1 /nobreak >nul
curl -s http://localhost:%FRONTEND_PORT% >nul 2>&1
if errorlevel 1 goto wait_frontend
echo [FRONTEND] Ready on http://localhost:%FRONTEND_PORT%

:: Open browser
echo.
echo  ========================================
echo   JAT-AI running at http://localhost:%FRONTEND_PORT%
echo   Press Ctrl+C to stop
echo  ========================================
echo.
start "" http://localhost:%FRONTEND_PORT%

:: Keep alive
:loop
timeout /t 5 /nobreak >nul
goto loop
