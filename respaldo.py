"""Copia de seguridad de la base de datos a una carpeta local sincronizada de Google Drive.

No usa la API de Google (que exigiría dar de alta un proyecto en Google Cloud y volver a
autenticar cada pocos días mientras la app no esté verificada por Google). En vez de eso,
se apoya en Google Drive para escritorio: la app deja una copia del fichero en una carpeta
normal de Windows, y es la propia aplicación de Drive (ya instalada y con la sesión iniciada
con la cuenta configurada para el correo) la que se encarga de subirla.
"""
import sqlite3
from datetime import datetime
from pathlib import Path

import database as db

DB_PATH = Path(__file__).parent / "data" / "app.db"


def hacer_backup():
    """Devuelve (ok, mensaje). No lanza excepción: un fallo aquí no debe impedir el cierre."""
    carpeta = db.get_config("drive_backup_folder")
    if not carpeta:
        return False, "no hay carpeta de copia de seguridad configurada en Configuración"

    destino_dir = Path(carpeta)
    if not destino_dir.exists() or not destino_dir.is_dir():
        return False, f"la carpeta configurada no existe: {carpeta}"

    marca = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    destino = destino_dir / f"panaderia_backup_{marca}.db"

    try:
        origen_conn = sqlite3.connect(str(DB_PATH))
        destino_conn = sqlite3.connect(str(destino))
        with destino_conn:
            origen_conn.backup(destino_conn)
        destino_conn.close()
        origen_conn.close()
        return True, f"Copia de seguridad guardada como {destino.name}"
    except Exception as e:
        return False, f"no se ha podido guardar la copia de seguridad: {e}"
