@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title NOMIKO - Windows launcher

echo ==========================================
echo        NOMIKO - Starting browser
echo ==========================================
echo.

rem Prefer the user's existing Python 3.15. Do not install a new interpreter.
set "PY_CMD="
where py >nul 2>nul
if errorlevel 1 goto :check_python_path

py -3.15 -c "import sys; assert sys.version_info[:2] == (3, 15) and sys.maxsize > 2**32" >nul 2>nul
if not errorlevel 1 set "PY_CMD=py -3.15"
if defined PY_CMD goto :python_found

py -3 -c "import sys; assert (3, 10) <= sys.version_info[:2] < (3, 16) and sys.maxsize > 2**32" >nul 2>nul
if not errorlevel 1 set "PY_CMD=py -3"
if defined PY_CMD goto :python_found

:check_python_path
python -c "import sys; assert (3, 10) <= sys.version_info[:2] < (3, 16) and sys.maxsize > 2**32" >nul 2>nul
if not errorlevel 1 set "PY_CMD=python"
if defined PY_CMD goto :python_found

echo [ERROR] Cannot find a compatible 64-bit Python 3.10-3.15 installation.
echo Check the installed interpreter with: py -0p
goto :fail

:python_found
echo Using installed Python:
%PY_CMD% --version
if errorlevel 1 goto :fail

rem A previous NOMIKO launch may have left a broken virtual environment.
if exist ".venv\" if not exist ".venv\Scripts\python.exe" (
    echo Removing incomplete NOMIKO virtual environment...
    rmdir /s /q ".venv"
    if errorlevel 1 goto :fail
)
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "import sys; assert (3, 10) <= sys.version_info[:2] < (3, 16)" >nul 2>nul
    if errorlevel 1 (
        echo Repairing incompatible NOMIKO virtual environment...
        rmdir /s /q ".venv"
        if errorlevel 1 goto :fail
    )
)

if not exist ".venv\Scripts\python.exe" (
    echo Creating NOMIKO virtual environment using your Python...
    %PY_CMD% -m venv ".venv"
    if errorlevel 1 goto :fail
)
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] NOMIKO virtual environment did not create a Python executable.
    goto :fail
)

echo.
echo Installing the matching Qt WebEngine components...
".venv\Scripts\python.exe" -m pip --version >nul 2>nul
if errorlevel 1 (
    ".venv\Scripts\python.exe" -m ensurepip --upgrade
    if errorlevel 1 goto :fail
)
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check --only-binary=:all: -r requirements.txt
if errorlevel 1 goto :fail

".venv\Scripts\python.exe" -c "from PySide6.QtWebEngineWidgets import QWebEngineView; import PySide6; print('Qt WebEngine is installed and importable.')"
if errorlevel 1 goto :fail

echo.
echo Launching NOMIKO...
".venv\Scripts\python.exe" main.py
if errorlevel 1 goto :fail
exit /b 0

:fail
echo.
echo [ERROR] NOMIKO did not launch. See the exact error above.
echo Your personal browsing data has not been reset.
pause
exit /b 1
