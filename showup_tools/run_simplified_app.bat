@echo off
setlocal enabledelayedexpansion
echo Starting ShowupSquared Simplified Content Generator...

REM Set UTF-8 encoding for all Python processes
set PYTHONIOENCODING=utf-8

REM Check if Python is installed
python --version > nul 2>&1
if !errorlevel! neq 0 (
    echo Python is not installed or not in the PATH.
    echo Please install Python 3.8+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Check if pandas is installed (main dependency)
python -c "import pandas" > nul 2>&1
if !errorlevel! neq 0 (
    echo Pandas is not installed. Installing required dependencies...
    pip install pandas
    if !errorlevel! neq 0 (
        echo Failed to install dependencies.
        pause
        exit /b 1
    )
)

REM Set the base directory to the script location
set "BASE_DIR=%~dp0"
cd /d "%BASE_DIR%"

REM Create required directories if they don't exist
if not exist "logs" mkdir "logs"
if not exist "logs\prompts" mkdir "logs\prompts"
if not exist "data" mkdir "data"
if not exist "templates" mkdir "templates"
if not exist "output" mkdir "output"
if not exist "cache" mkdir "cache"
if not exist "archive" mkdir "archive"
if not exist "test_data" mkdir "test_data"

REM Define the output directory path without quotes in the variable
set "OUTPUT_DIR=..\..\..\library\Physical Education\Course Material"

REM Create the designated output directory if it doesn't exist
if not exist "!OUTPUT_DIR!" mkdir "!OUTPUT_DIR!"

REM Run the application
echo.
echo Starting Simplified Content Generator application...
echo.

REM Check if arguments were provided
if "%1"=="" (
    REM No arguments, run with defaults and specified output directory
    python simplified_app.py --output-dir "!OUTPUT_DIR!"
) else (
    REM Pass all arguments to the Python script along with output directory
    python simplified_app.py --output-dir "!OUTPUT_DIR!" %*
)

pause
endlocal