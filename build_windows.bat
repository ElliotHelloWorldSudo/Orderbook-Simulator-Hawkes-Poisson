@echo off
REM Build a standalone Windows executable (onedir) with PyInstaller.
REM Run this ON WINDOWS from the project root:  build_windows.bat
setlocal

cd /d "%~dp0"

echo ==^> Creating virtual environment (.venv)
python -m venv .venv
call .venv\Scripts\activate.bat

echo ==^> Installing dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

echo ==^> Cleaning previous build artifacts
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul

echo ==^> Running PyInstaller
pyinstaller packaging\app.spec --noconfirm

echo.
echo ==^> Build complete.
echo     Standalone app folder: dist\OrderBookSimulator\
echo     Launch it with:        dist\OrderBookSimulator\OrderBookSimulator.exe
echo.
echo ==^> To produce an installable Setup.exe, install Inno Setup
echo     (https://jrsoftware.org/isinfo.php) then run:
echo     packaging\windows\build_installer.bat
endlocal
