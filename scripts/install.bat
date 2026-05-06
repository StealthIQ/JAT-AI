@echo off
:: Adds "jat" command to your system PATH so you can run it from anywhere.
:: Run this once as Administrator.

set SCRIPT_DIR=%~dp0
set TARGET=%USERPROFILE%\jat.cmd

echo @echo off > "%TARGET%"
echo call "%SCRIPT_DIR%jat.bat" %%* >> "%TARGET%"

:: Add user profile to PATH if not already there
echo %PATH% | findstr /i "%USERPROFILE%" >nul
if errorlevel 1 (
    setx PATH "%PATH%;%USERPROFILE%"
    echo [OK] Added %USERPROFILE% to PATH.
) else (
    echo [OK] %USERPROFILE% already in PATH.
)

:: Install Python dependencies including chromadb
pip install -e . >nul 2>&1
echo [OK] Python dependencies installed.
echo [NOTE] First run may download embedding models (~100MB).

echo [OK] "jat" command installed. Open a new terminal and type: jat
pause
