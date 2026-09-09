@echo off
setlocal
cd /d "%~dp0"

echo Buscando actualizaciones...
git pull --ff-only >nul 2>&1

echo Comprobando dependencias...
venv\Scripts\python.exe -m pip install -q -r requirements.txt >nul 2>&1

if not exist config.py (
    echo No existe config.py, lo creo a partir de config.example.py...
    copy /y config.example.py config.py >nul
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
