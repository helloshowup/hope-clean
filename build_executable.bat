@echo off
REM Build workflow_app executable using PyInstaller
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

pyinstaller --clean --noconfirm workflow_app.spec
