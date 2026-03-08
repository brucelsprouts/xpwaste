@echo off
title XP Waste Setup
color 0A

echo.
echo ================================
echo   XP Waste Setup
echo ================================
echo.

echo Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.7+ from python.org
    echo.
    pause
    exit /b 1
)

echo Python found! Installing dependencies...
echo.

pip install PyQt5

if errorlevel 1 (
    echo.
    echo WARNING: pip install failed. Trying alternative method...
    python -m pip install PyQt5
)

echo.
echo ================================
echo   Setup Complete!
echo ================================
echo.
echo To run XP Waste:
echo 1. Double-click "run_xp_waste.pyw"
echo 2. Or run "python main.py" in terminal
echo.
echo To create a standalone executable:
echo 1. Run "build_executable.bat"
echo.
pause