@echo off
setlocal
title CPU Scheduling Optimizer PRO
cd /d "%~dp0"

echo ============================================================
echo   CPU Scheduling ^& Process Optimization System v1.0
echo ============================================================
echo.

:: -- Python detection --------------------------------------------------------
set PY=
where py >nul 2>nul && set PY=py
if "!PY!"=="" where python >nul 2>nul && set PY=python
if "!PY!"=="" (
    echo [ERROR] Python 3 not found. Install from https://python.org and retry.
    pause
    exit /b 1
)

:: -- Verify Python 3 ---------------------------------------------------------
%PY% -c "import sys; sys.exit(0 if sys.version_info >= (3,8) else 1)" >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python 3.8+ required. Found older version.
    %PY% --version
    pause
    exit /b 1
)

:: -- Install / verify dependencies --------------------------------------------
echo Checking dependencies...
%PY% -c "import psutil, matplotlib" >nul 2>nul
if errorlevel 1 (
    echo Installing required packages (psutil, matplotlib^)...
    %PY% -m pip install -r requirements.txt --quiet
    if errorlevel 1 (
        echo [ERROR] Failed to install packages. Run manually:
        echo   pip install psutil matplotlib
        pause
        exit /b 1
    )
    echo Dependencies installed successfully.
)

:: -- Launch GUI ---------------------------------------------------------------
echo Starting GUI...
echo.
%PY% gui.py
if errorlevel 1 (
    echo.
    echo [ERROR] GUI exited with an error.
    pause
)

endlocal
