@echo OFF
setlocal

REM --- Navigate to the Project Root Directory ---
ECHO Navigating to the project root from %~dp0...
cd /d "%~dp0\..\..\.."

REM --- Activate Virtual Environment ---
ECHO Activating virtual environment...
CALL venv\Scripts\activate.bat

REM --- Install the project in editable mode ---
ECHO Installing project in editable mode...
pip install -e .

REM --- Run the application ---
ECHO Starting the Simplified Content Generator...
python -m showup_tools.simplified_app.simplified_main

REM --- Deactivate ---
ECHO Deactivating virtual environment...
CALL venv\Scripts\deactivate.bat

endlocal
pause
