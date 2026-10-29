@echo off
setlocal EnableExtensions
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
 echo First run run-windows.bat to install browser dependencies.
 pause
 exit /b 1
)
".venv\Scripts\python.exe" -m pip install --upgrade pyinstaller
if errorlevel 1 goto :fail
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --windowed --onedir --name NOMIKO --collect-all PySide6.QtWebEngineCore --collect-all PySide6.QtWebEngineWidgets main.py
if errorlevel 1 goto :fail
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onefile --windowed --name NOMIKO-UpdateHelper --distpath helper-dist update_helper.py
if errorlevel 1 goto :fail
copy /Y "helper-dist\NOMIKO-UpdateHelper.exe" "dist\NOMIKO\NOMIKO-UpdateHelper.exe" >NUL
if errorlevel 1 goto :fail
echo.
echo Portable EXE built at dist\NOMIKO\NOMIKO.exe
if exist "dist\NOMIKO\NOMIKO.exe" explorer "dist\NOMIKO"
echo To build an installer, install NSIS and run makensis installer\NOMIKO.nsi
pause
exit /b 0
:fail
echo EXE build failed. Review errors above.
pause
exit /b 1
