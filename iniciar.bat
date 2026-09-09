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
start "Gestion interna" /min cmd /c "venv\Scripts\python.exe app.py"
timeout /t 2 /nobreak >nul
start "" http://127.0.0.1:5000
