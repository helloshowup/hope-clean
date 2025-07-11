:: ============================================================================
:: File: run_generator.bat
:: ============================================================================
@echo off
setlocal enabledelayedexpansion

echo Starting ShowupSquared Simplified Content Generator...

:: Set UTF-8 encoding for all Python processes
set PYTHONIOENCODING=utf-8

:: --- Python and Dependency Checks ---
echo.
echo Checking for Python and required libraries...

:: 1. Check for Python
python --version > nul 2>&1
if !errorlevel! neq 0 (
    echo [ERROR] Python is not installed or not in the PATH.
    echo Please install Python 3.8+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

:: 2. Check for requirements.txt and install dependencies
if not exist "requirements.txt" (
    echo [ERROR] requirements.txt not found! Cannot verify dependencies.
    pause
    exit /b 1
)

echo Installing/verifying libraries from requirements.txt...
python -m pip install -r requirements.txt
if !errorlevel! neq 0 (
    echo [ERROR] Failed to install dependencies from requirements.txt.
    echo Please check your internet connection and pip installation.
    pause
    exit /b 1
)
echo Dependencies are up to date.

:: --- Directory Setup ---
set "BASE_DIR=%~dp0"
cd /d "%BASE_DIR%"

echo.
echo Ensuring required directories exist...
if not exist "logs" mkdir "logs"
if not exist "output" mkdir "output"
if not exist "output\generation_results" mkdir "output\generation_results"
if not exist "output\comparison_results" mkdir "output\comparison_results"
if not exist "cache" mkdir "cache"

:: Define the final output directory for the generated content
set "FINAL_OUTPUT_DIR=..\..\..\library\Physical Education\Course Material"

:: Create the designated output directory if it doesn't exist
if not exist "!FINAL_OUTPUT_DIR!" mkdir "!FINAL_OUTPUT_DIR!"

:: --- Run Application ---
echo.
echo Starting Simplified Content Generator application...
echo.

:: Check if arguments were provided to the batch script
if "%1"=="" (
    :: No arguments, run with defaults and specified output directory
    python simplified_app.py --output-dir "!FINAL_OUTPUT_DIR!"
) else (
    :: Pass all batch script arguments to the Python script
    python simplified_app.py --output-dir "!FINAL_OUTPUT_DIR!" %*
)

echo.
echo Script finished. Press any key to exit.
pause
endlocal


:: ============================================================================
:: File: requirements.txt
:: (Save this in the same directory as the batch file)
:: ============================================================================
pandas
torch
sentence-transformers
