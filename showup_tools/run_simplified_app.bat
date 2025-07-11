@echo off
setlocal enabledelayedexpansion

echo Starting ShowupSquared Simplified Content Generator...

REM Set UTF-8 encoding for all Python processes
set "PYTHONIOENCODING=utf-8"

REM Set the base directory to the script's location
set "BASE_DIR=%~dp0"
cd /d "%BASE_DIR%"

REM ============================================================================
REM == Virtual Environment and Dependency Setup
REM ============================================================================

REM Check if Python is installed
python --version > nul 2>&1
if !errorlevel! neq 0 (
    echo [ERROR] Python is not installed or not found in your system's PATH.
    echo Please install Python 3.8+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Define the absolute path to the central requirements file
set "REQUIREMENTS_FILE=D:\000-SIBU\hope\requirements.txt"

REM Check if requirements.txt exists at the specified path
if not exist "!REQUIREMENTS_FILE!" (
    echo [ERROR] requirements.txt file not found at !REQUIREMENTS_FILE!.
    echo Cannot install dependencies.
    pause
    exit /b 1
)

REM Create a virtual environment in the current directory if it doesn't exist
if not exist "venv" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
)

REM Activate the virtual environment
echo [INFO] Activating virtual environment...
if exist "%BASE_DIR%venv\Scripts\activate.bat" (
    call "%BASE_DIR%venv\Scripts\activate.bat"
) else (
    echo [ERROR] Virtual environment not found at "%BASE_DIR%venv".
    pause
    exit /b 1
)

REM Install all dependencies from the central requirements.txt file
echo [INFO] Installing/updating dependencies from !REQUIREMENTS_FILE!...
pip install -r "!REQUIREMENTS_FILE!"

REM ============================================================================
REM == Application Setup and Execution
REM ============================================================================

REM Create required application directories if they don't exist
echo [INFO] Checking for required directories...
if not exist "logs" mkdir "logs"
if not exist "logs\prompts" mkdir "logs\prompts"
if not exist "data" mkdir "data"
if not exist "templates" mkdir "templates"
if not exist "output" mkdir "output"
if not exist "cache" mkdir "cache"
if not exist "archive" mkdir "archive"
if not exist "test_data" mkdir "test_data"

REM Define the output directory path
set "OUTPUT_DIR=..\..\..\library\Physical Education\Course Material"

REM Create the designated output directory if it doesn't exist
if not exist "!OUTPUT_DIR!" mkdir "!OUTPUT_DIR!"

REM Run the application
echo.
echo [INFO] Starting Simplified Content Generator application...
echo.

REM Check if arguments were provided and run the python script
if "%1"=="" (
    REM No arguments, run with defaults and specified output directory
    python "simplified_app.py" --output-dir "!OUTPUT_DIR!"
) else (
    REM Pass all arguments to the Python script along with output directory
    python "simplified_app.py" --output-dir "!OUTPUT_DIR!" %*
)

pause
endlocal
