@echo off
title Structural Calculation App - US Engineering
echo =====================================================================
echo Launching Structural Calculation Application (PySide6 Desktop)...
echo =====================================================================
cd /d "%~dp0"
"C:\Users\minhn\.venv_struct\Scripts\python.exe" main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Application exited with error code %ERRORLEVEL%.
    pause
)
