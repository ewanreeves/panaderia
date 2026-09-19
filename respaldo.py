"""Copia de seguridad local de la base de datos, en cada cierre de turno.

Se guarda en backups/ (dentro de la propia carpeta de la app), con cuatro niveles de
retención tipo "abuelo-padre-hijo": diario, semanal, mensual y anual. Cada cierre añade
la copia del día en backups/diario, y si es la primera copia de esa semana/mes/año,
también la deja en backups/semanal, backups/mensual y backups/anual. Cada carpeta se
poda por su cuenta a un máximo de ficheros, así que las copias ya promovidas a un nivel
superior no desaparecen cuando se poda un nivel inferior.

No usa ningún servicio en la nube: son copias en el propio PC de la clienta.
"""
import shutil
import sqlite3
from datetime import date
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "app.db"
BACKUPS_DIR = Path(__file__).parent / "backups"

RETENCION = {
    "diario": 5,
    "semanal": 4,
    "mensual": 12,
    "anual": 5,
}


def _clave_periodo(nivel, hoy):
    if nivel == "diario":
        return hoy.isoformat()
    if nivel == "semanal":
        iso_year, iso_week, _ = hoy.isocalendar()
        return f"{iso_year}-W{iso_week:02d}"
    if nivel == "mensual":
        return f"{hoy.year}-{hoy.month:02d}"
    if nivel == "anual":
        return str(hoy.year)
    raise ValueError(nivel)


def _podar(carpeta_dir, maximo):
    archivos = sorted(carpeta_dir.glob("app_*.db"))
    de_mas = max(0, len(archivos) - maximo)
    for f in archivos[:de_mas]:
        f.unlink(missing_ok=True)


def hacer_backup():
    """Devuelve (ok, mensaje). No lanza excepción: un fallo aquí no debe impedir el cierre."""
    hoy = date.today()
    try:
        for nivel in RETENCION:
            (BACKUPS_DIR / nivel).mkdir(parents=True, exist_ok=True)

        destino_diario = BACKUPS_DIR / "diario" / f"app_{_clave_periodo('diario', hoy)}.db"
        origen_conn = sqlite3.connect(str(DB_PATH))
        destino_conn = sqlite3.connect(str(destino_diario))
        with destino_conn:
            origen_conn.backup(destino_conn)
        destino_conn.close()
        origen_conn.close()

        for nivel in ("semanal", "mensual", "anual"):
            destino = BACKUPS_DIR / nivel / f"app_{_clave_periodo(nivel, hoy)}.db"
            shutil.copyfile(destino_diario, destino)

        for nivel, maximo in RETENCION.items():
            _podar(BACKUPS_DIR / nivel, maximo)

        return True, f"Copia de seguridad guardada ({destino_diario.name})"
    except Exception as e:
        return False, f"no se ha podido guardar la copia de seguridad: {e}"
