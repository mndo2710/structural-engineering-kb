@echo off
setlocal
title Structural Calculation App - US Engineering
echo =====================================================================
echo Launching Structural Calculation Application (PySide6 Desktop)...
echo =====================================================================
cd /d "%~dp0"

set "PYTHON_EXE="
if exist "C:\Users\nhatdo\.venv_struct\Scripts\python.exe" (
    set "PYTHON_EXE=C:\Users\nhatdo\.venv_struct\Scripts\python.exe"
) else if exist ".venv_struct\Scripts\python.exe" (
    set "PYTHON_EXE=.venv_struct\Scripts\python.exe"
) else if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
) else (
    where python >nul 2>nul
    if %ERRORLEVEL% EQU 0 (
        set "PYTHON_EXE=python"
    )
)

if "%PYTHON_EXE%"=="" (
    echo ERROR: Python virtual environment not found.
    echo Checked: C:\Users\nhatdo\.venv_struct, .venv_struct, .venv, and PATH.
    pause
    exit /b 1
)

echo Using Python: %PYTHON_EXE%
"%PYTHON_EXE%" main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Application exited with error code %ERRORLEVEL%.
    pause
)
endlocal
