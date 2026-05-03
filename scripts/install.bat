@echo off
:: Adds "jai" command to your system PATH so you can run it from anywhere.
:: Run this once as Administrator.

set SCRIPT_DIR=%~dp0
set TARGET=%USERPROFILE%\jai.cmd

echo @echo off > "%TARGET%"
echo call "%SCRIPT_DIR%jai.bat" %%* >> "%TARGET%"

:: Add user profile to PATH if not already there
echo %PATH% | findstr /i "%USERPROFILE%" >nul
if errorlevel 1 (
    setx PATH "%PATH%;%USERPROFILE%"
    echo [OK] Added %USERPROFILE% to PATH.
) else (
    echo [OK] %USERPROFILE% already in PATH.
)

echo [OK] "jai" command installed. Open a new terminal and type: jai
pause
