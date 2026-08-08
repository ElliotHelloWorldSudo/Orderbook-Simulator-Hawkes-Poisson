@echo off
REM Compiles installer.iss into a real Setup.exe using the Inno Setup
REM command-line compiler (ISCC.exe). Requires Inno Setup to be installed:
REM   https://jrsoftware.org/isinfo.php
setlocal
cd /d "%~dp0"

set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist %ISCC% (
    echo Could not find ISCC.exe at the default install path.
    echo Edit this script or add ISCC.exe to your PATH, then re-run.
    echo Download Inno Setup from https://jrsoftware.org/isinfo.php
    exit /b 1
)

%ISCC% installer.iss

echo.
echo ==^> Installer created in packaging\windows\Output\OrderBookSimulator-Setup.exe
endlocal
