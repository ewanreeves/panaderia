@echo off
setlocal
cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1"
if errorlevel 1 (
    echo.
    echo No se ha podido preparar la app. Revisa el mensaje de arriba.
    pause
    exit /b 1
)

echo Iniciando Gestion interna...
start "Gestion interna" venv\Scripts\pythonw.exe app.py
timeout /t 2 /nobreak >nul

set URL=http://127.0.0.1:5000

set EDGE="%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
if not exist %EDGE% set EDGE="%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"
set CHROME="%ProgramFiles%\Google\Chrome\Application\chrome.exe"
if not exist %CHROME% set CHROME="%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"

if exist %EDGE% (
    start "" %EDGE% --app=%URL% --window-size=1280,860
) else if exist %CHROME% (
    start "" %CHROME% --app=%URL% --window-size=1280,860
) else (
    start "" %URL%
)
