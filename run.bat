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

py -m pip install --quiet --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
    echo Errore installazione dipendenze.
    pause
    exit /b 1
)

start "" pyw app.py
