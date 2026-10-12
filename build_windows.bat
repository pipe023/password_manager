@echo off
setlocal
cd /d "%~dp0"

set "PYTHON=venv\Scripts\python.exe"
if not exist "%PYTHON%" (
    echo Python environment not found at "%PYTHON%".
    echo Create the project venv and install requirements-build.txt first.
    exit /b 1
)

"%PYTHON%" -m pip install -r requirements-build.txt
if errorlevel 1 exit /b 1

"%PYTHON%" -c "from PIL import Image; Image.open('assets/pymanager_logo.png').save('assets/pymanager.ico', format='ICO', sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])"
if errorlevel 1 exit /b 1

"%PYTHON%" -m PyInstaller --noconfirm --clean --onefile --windowed --name PyManager --icon "%~dp0assets\pymanager.ico" --add-data "%~dp0assets\pymanager_logo.png;assets" --distpath "dist\release" --workpath "build\release" --specpath "build\spec" gui.py
if errorlevel 1 exit /b 1

echo.
echo Build complete: "%~dp0dist\release\PyManager.exe"
echo The encrypted vault will be stored under %%LOCALAPPDATA%%\PyManager.
endlocal
