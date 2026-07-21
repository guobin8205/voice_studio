@echo off
cd /d "%~dp0"

echo.
echo   TTS Studio
echo   ==========
echo.
echo   Starting...

REM Try python, py, python3
set PYTHON=
where python  >nul 2>&1 && set PYTHON=python
where py      >nul 2>&1 && set PYTHON=py
where python3 >nul 2>&1 && set PYTHON=python3

if "%PYTHON%"=="" (
    echo   Python not found in PATH
    echo   Please install Python 3.10+: https://www.python.org/
    pause
    exit /b 1
)

%PYTHON% run.py %*
if errorlevel 1 (
    pause
)
