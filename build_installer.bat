@echo off
setlocal
cd /d "%~dp0"

set "ISCC="
where ISCC.exe >nul 2>nul
if not errorlevel 1 set "ISCC=ISCC.exe"

if not defined ISCC if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"

if not defined ISCC (
    echo Inno Setup 6 compiler was not found.
    echo Install Inno Setup 6, then run this script again.
    exit /b 1
)

if not exist "dist\release\PyManager.exe" (
    echo Application executable not found.
    echo Run build_windows.bat first.
    exit /b 1
)

"%ISCC%" "installer\PyManager.iss"
if errorlevel 1 exit /b 1

echo.
echo Installer created in "%~dp0dist\installer".
endlocal
