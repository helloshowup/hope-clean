@echo off
REM ───────────────────────────────────────────────────────────────
REM  Launch Modular Editor – self-healing environment
REM ───────────────────────────────────────────────────────────────
setlocal EnableDelayedExpansion

REM ► Project root (one dir up from this script)
set "PROJECT_ROOT=%~dp0.."

REM ► Paths for PYTHONPATH (underscore folder + editor-ui folder)
set "PYTHONPATH=%PROJECT_ROOT%;%PROJECT_ROOT%\showup-core;%PROJECT_ROOT%\showup_tools;%~dp0"

REM ► Ensure virtual-env exists
if not exist "%PROJECT_ROOT%\showup-core\venv\Scripts\python.exe" (
    echo [+] Creating venv...
    python -m venv "%PROJECT_ROOT%\showup-core\venv"
)

REM ► Use venv’s python
set "PYTHON=%PROJECT_ROOT%\showup-core\venv\Scripts\python.exe"

REM ► Upgrade pip quietly (skips if up-to-date)
%PYTHON% -m pip install --upgrade pip --disable-pip-version-check -q

REM ► Install/update core requirements
echo [+] Checking deps...
%PYTHON% -m pip install -r "%PROJECT_ROOT%\showup-core\requirements.txt" -q

REM ► Extra packages you know you need (edit list as needed)
%PYTHON% -m pip install tiktoken langchain openai faiss-cpu sentence-transformers -q

REM ► Launch editor UI
cd /d "%~dp0"
echo [+] Starting editor...
echo Using : %PYTHON%
echo PYTHONPATH : %PYTHONPATH%
echo. > launch.log
echo ==== LAUNCH %date% %time% ==== >> launch.log
%PYTHON% -m claude_panel.main >> launch.log 2>&1
if errorlevel 1 (
    echo [!] Launch failed – see launch.log
) else (
    echo [✓] Editor closed normally.
)
pause
endlocal
