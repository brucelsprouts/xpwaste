@echo off
title Build XP Waste Executable
color 0B

echo.
echo ====================================
echo   Building XP Waste Executable
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

if exist "../assets/xpwaste.ico" (
    echo Using custom icon: assets\xpwaste.ico
    python -m PyInstaller --onefile --windowed ^
        --distpath "../dist" ^
        --workpath "../build" ^
        --add-data "../data;data" ^
        --add-data "../assets;assets" ^
        --icon "../assets/xpwaste.ico" ^
        --name "XPWaste" ^
        --clean ^
        ../source/main.py
) else if exist "../xp icon.ico" (
    echo Using custom icon: xp icon.ico
    python -m PyInstaller --onefile --windowed ^
        --distpath "../dist" ^
        --workpath "../build" ^
        --add-data "../data;data" ^
        --add-data "../assets;assets" ^
        --icon "../xp icon.ico" ^
        --name "XPWaste" ^
        --clean ^
        ../source/main.py
) else (
    echo No icon found, building without custom icon.
    python -m PyInstaller --onefile --windowed ^
        --distpath "../dist" ^
        --workpath "../build" ^
        --add-data "../data;data" ^
        --add-data "../assets;assets" ^
        --name "XPWaste" ^
        --clean ^
        ../source/main.py
)

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
echo Moving executable to main folder...
if exist "../dist/XPWaste.exe" (
    move "../dist/XPWaste.exe" "../XPWaste.exe"
    rmdir "../dist"
)
echo.
echo Your executable is ready:
echo Location: %cd%\..\XPWaste.exe
echo.
echo You can now:
echo 1. Run XPWaste.exe directly (in main folder)
echo 2. Move it anywhere and run it
echo 3. Share it with others (no Python needed)
echo.

if exist "../XPWaste.exe" (
    echo Opening main folder...
    start "" ".."
)

echo.
pause