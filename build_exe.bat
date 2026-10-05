@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
    echo Python non trovato.
    echo Installa Python 3 da python.org e abilita "Add Python to PATH".
    pause
    exit /b 1
)

echo Installazione dipendenze...
py -m pip install --upgrade pip
py -m pip install pillow pyinstaller

echo.
echo Creazione EXE Windows...
py -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --onefile ^
    --windowed ^
    --name "NDSIconMaker" ^
    app.py

if errorlevel 1 (
    echo.
    echo Build fallita.
    pause
    exit /b 1
)

echo.
echo EXE creato:
echo %cd%\dist\NDSIconMaker.exe
explorer /select,"%cd%\dist\NDSIconMaker.exe"
pause
