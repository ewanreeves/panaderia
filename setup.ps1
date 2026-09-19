# setup.ps1 - deja esta carpeta lista para arrancar en cualquier PC con Windows:
# instala Git y Python si faltan, trae la ultima version del codigo, crea (o repara)
# el entorno virtual y las dependencias, y prepara config.py si no existe.
#
# Pensado para poder copiar la carpeta entera del proyecto a un PC limpio y que
# arranque solo con iniciar.bat, sin instalar nada a mano de antemano.
#
# Requisitos que esto NO puede saltarse:
#   - Conexion a internet la primera vez (para descargar Git/Python/dependencias).
#   - Windows con "winget" (viene de fabrica en Windows 10 reciente y en Windows 11).
#   - Si Windows pide permiso de administrador para instalar Git o Python, hay que
#     aceptarlo una vez; eso lo pide Windows, no lo puede evitar este script.
#
# Si algo falla de verdad, este script termina con un mensaje claro y un codigo de
# salida distinto de cero; iniciar.bat lo detecta y para ahi en vez de fallar en
# silencio.

Set-Location -Path $PSScriptRoot

function Refrescar-Path {
    $machine = [System.Environment]::GetEnvironmentVariable('Path', 'Machine')
    $usuario = [System.Environment]::GetEnvironmentVariable('Path', 'User')
    $env:Path = @($machine, $usuario) -join ';'
}

function Tiene-Comando($nombre) {
    return [bool](Get-Command $nombre -ErrorAction SilentlyContinue)
}

function Instalar-Con-Winget($id, $nombre, $urlManual) {
    if (-not (Tiene-Comando 'winget')) {
        Write-Host ""
        Write-Host "Falta $nombre y este Windows no tiene 'winget' (el instalador de apps) para ponerlo solo."
        Write-Host "Instala $nombre a mano desde $urlManual y vuelve a hacer doble clic en iniciar.bat."
        exit 1
    }
    Write-Host "Instalando $nombre (una sola vez, puede tardar unos minutos)..."
    winget install --id $id -e --silent --accept-package-agreements --accept-source-agreements | Out-Host
    if ($LASTEXITCODE -ne 0) {
        Write-Host "No se ha podido instalar $nombre solo (codigo $LASTEXITCODE)."
        Write-Host "Instalalo a mano desde $urlManual y vuelve a hacer doble clic en iniciar.bat."
        exit 1
    }
    Refrescar-Path
}

Write-Host "Comprobando Git..."
if (-not (Tiene-Comando 'git')) {
    Instalar-Con-Winget 'Git.Git' 'Git' 'https://git-scm.com/download/win'
}

Write-Host "Comprobando Python..."
if (-not (Tiene-Comando 'py') -and -not (Tiene-Comando 'python')) {
    Instalar-Con-Winget 'Python.Python.3.12' 'Python' 'https://www.python.org/downloads/'
}
Refrescar-Path
if (-not (Tiene-Comando 'py') -and -not (Tiene-Comando 'python')) {
    Write-Host "Python se acaba de instalar pero esta ventana todavia no lo detecta."
    Write-Host "Cierra esta ventana y haz doble clic en iniciar.bat otra vez."
    exit 1
}
$pythonCmd = if (Tiene-Comando 'py') { 'py' } else { 'python' }

if ((Tiene-Comando 'git') -and (Test-Path '.git')) {
    Write-Host "Buscando actualizaciones..."
    git pull --ff-only
}

# El venv puede venir roto si la carpeta se copio de otro PC (Python estaba en otra ruta)
$venvOk = $false
if (Test-Path 'venv\Scripts\python.exe') {
    & 'venv\Scripts\python.exe' -c "import os" *> $null
    if ($LASTEXITCODE -eq 0) { $venvOk = $true }
}
if (-not $venvOk) {
    if (Test-Path 'venv') {
        Write-Host "El entorno virtual (venv) no funciona en este PC (seguramente se copio de otro equipo). Lo recreo..."
        try {
            Remove-Item -Recurse -Force 'venv' -ErrorAction Stop
        } catch {
            Write-Host "No se ha podido borrar el venv roto: $_"
            exit 1
        }
    } else {
        Write-Host "No existe el entorno virtual. Lo creo..."
    }
    & $pythonCmd -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "No se ha podido crear el entorno virtual."
        exit 1
    }
}

Write-Host "Comprobando dependencias..."
& 'venv\Scripts\python.exe' -m pip install -q -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "No se han podido instalar las dependencias."
    exit 1
}

if (-not (Test-Path 'config.py')) {
    Write-Host "No existe config.py, lo creo a partir de config.example.py..."
    try {
        Copy-Item 'config.example.py' 'config.py' -ErrorAction Stop
    } catch {
        Write-Host "No se ha podido crear config.py: $_"
        exit 1
    }
}

exit 0
