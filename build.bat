@echo off
REM TaxGlide Build Script Wrapper
REM This batch file calls the PowerShell build script

echo Starting TaxGlide Nuitka Build...
echo.

REM Check if we're in the right directory
if not exist "main.py" (
    echo Error: main.py not found. Please run this script from the TaxGlide project root.
    pause
    exit /b 1
)

REM Check if PowerShell is available
where powershell >nul 2>nul
if %errorlevel% neq 0 (
    echo Error: PowerShell not found. This script requires PowerShell.
    pause
    exit /b 1
)

REM Execute the PowerShell build script
powershell -ExecutionPolicy Bypass -File "build_executable.ps1"

if %errorlevel% equ 0 (
    echo.
    echo Build completed successfully!
    echo Executable location: dist\taxglide.exe
) else (
    echo.
    echo Build failed. Check the output above for details.
)

pause
