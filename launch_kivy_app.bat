@echo off
REM ShowupSquared Kivy App Launcher

REM Change directory to the location of this script (repo root)
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

ECHO Checking for Python...
where python >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    ECHO Python is not installed or not in PATH.
    pause
    exit /B 1
)

set VENV_DIR=venv
IF NOT EXIST "%VENV_DIR%\Scripts\activate.bat" (
    ECHO Creating virtual environment...
    python -m venv "%VENV_DIR%"
    IF %ERRORLEVEL% NEQ 0 (
        ECHO Failed to create virtual environment.
        pause
        exit /B 1
    )
)

CALL "%VENV_DIR%\Scripts\activate.bat"
IF %ERRORLEVEL% NEQ 0 (
    ECHO Failed to activate virtual environment.
    pause
    exit /B 1
)

IF EXIST requirements.txt (
    ECHO Installing dependencies from requirements.txt...
    pip install -r requirements.txt
    IF %ERRORLEVEL% NEQ 0 (
        ECHO Failed to install required packages.
        pause
        exit /B 1
    )
) ELSE (
    ECHO requirements.txt not found. Skipping dependency installation.
)

REM Set environment variables for the workflow prompts
set "PYTHONPATH=%CD%"
set "PLANNING_PROMPT=prompts/planning/main_lesson_planner.txt"
set "REFINEMENT_PROMPT=prompts/planning/plan_refine_prompt.txt"
set "GENERATION_PROMPT=prompts/generation/generation_prompt.txt"
set "COMPARISON_PROMPT=prompts/review/content_comparison_prompt.txt"
set "REVIEW_PROMPT=prompts/review/content_review_prompt.txt"


ECHO Launching Kivy application...
REM Added '--' to separate Kivy arguments from application arguments
python main.py -- --csv_file data/test_input.csv --course_name "Introduction to Academic Grit" --log_level DEBUG
IF %ERRORLEVEL% NEQ 0 (
    ECHO Kivy application exited with errors.
    pause
    exit /B %ERRORLEVEL%
)

ECHO Kivy application closed.
pause
