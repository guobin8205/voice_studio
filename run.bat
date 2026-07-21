@echo off
cd /d "%~dp0"

echo.
echo   TTS Studio
echo   ==========
echo.
echo   Detecting Python...

REM Skip Microsoft Store alias, find real Python
set PYTHON=

REM Try py launcher first (most reliable on Windows)
where py >nul 2>&1
if %errorlevel% equ 0 (
    py --version >nul 2>&1
    if %errorlevel% equ 0 set PYTHON=py
)

REM Try python, excluding WindowsApps path
if "%PYTHON%"=="" (
    for /f "tokens=*" %%p in ('where python 2^>nul ^| findstr /v /i "WindowsApps"') do (
        %%p --version >nul 2>&1
        if %errorlevel% equ 0 (
            set PYTHON=%%p
            goto :found
        )
    )
)

REM Try python3
if "%PYTHON%"=="" (
    where python3 >nul 2>&1
    if %errorlevel% equ 0 set PYTHON=python3
)

:found
if "%PYTHON%"=="" (
    echo.
    echo   Python not found!
    echo.
    echo   Please install Python from: https://www.python.org/
    echo   During installation, check "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

echo   Found: %PYTHON%
%PYTHON% --version
echo.

%PYTHON% run.py %*
if errorlevel 1 pause
