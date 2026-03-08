@echo off
echo Cleaning up old/duplicate files...

if exist build_exe.bat (
    del build_exe.bat
    echo Removed: build_exe.bat
)

if exist build_simple.bat (
    del build_simple.bat  
    echo Removed: build_simple.bat
)

if exist EXECUTABLE_GUIDE.md (
    del EXECUTABLE_GUIDE.md
    echo Removed: EXECUTABLE_GUIDE.md
)

if exist pomodoro.pyw (
    del pomodoro.pyw
    echo Removed: pomodoro.pyw (replaced with run_pomodoro.pyw)
)

echo.
echo Cleanup complete! Repository is now organized.
echo Main files to use:
echo - run_xp_waste.pyw (to run the timer)
echo - setup.bat (to install dependencies) 
echo - build_executable.bat (to create .exe)
echo.
pause