@echo off
title Build XP Waste Timer Executable
color 0B

echo.
echo ====================================
echo   Building XP Waste Timer Executable
echo ====================================
echo.

echo Checking PyInstaller...
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
    echo.
)

echo Building standalone executable...
echo This may take a few minutes...
echo.

pyinstaller --onefile --windowed ^
    --distpath "./dist" ^
    --workpath "./build" ^
    --add-data "data;data" ^
    --name "XPWasteTimer" ^
    --clean ^
    main.py

if errorlevel 1 (
    echo.
    echo ERROR: Build failed!
    echo Make sure all dependencies are installed.
    pause
    exit /b 1
)

echo.
echo ====================================
echo   Build Successful!
echo ====================================
echo.
echo Your executable is ready:
echo Location: %cd%\dist\XPWasteTimer.exe
echo.
echo You can now:
echo 1. Run XPWasteTimer.exe directly
echo 2. Move it anywhere and run it
echo 3. Share it with others (no Python needed)
echo.

if exist "dist\XPWasteTimer.exe" (
    echo Opening dist folder...
    start "" "dist"
)

echo.
pause