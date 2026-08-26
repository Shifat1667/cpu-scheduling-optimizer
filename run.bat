@echo off
setlocal
title CPU Scheduling Optimizer
cd /d "%~dp0"
echo ============================================
echo   CPU Scheduling ^& Process Optimization
echo ============================================
echo.
echo Starting GUI...
where py >nul 2>nul
if not errorlevel 1 (
    py -3 gui.py
    goto :end
)

where python >nul 2>nul
if not errorlevel 1 (
    python gui.py
    goto :end
)

echo Python 3 was not found. Install Python 3 and try again.
pause

:end
endlocal
