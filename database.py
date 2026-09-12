import sqlite3
from datetime import datetime, date
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "app.db"

TIPOS = ("merma", "reciclaje", "autoconsumo", "errores")

TIPO_LABELS = {
    "merma": "Merma",
    "reciclaje": "Reciclaje",
    "autoconsumo": "Autoconsumo",
    "errores": "Errores",
}

TIPO_ICONOS = {
    "merma": "🗑️",
    "reciclaje": "♻️",
    "autoconsumo": "🍽️",
    "errores": "🗯️",
}

CATEGORIA_ICONOS = {
    "Bebidas": "🥤",
    "Cafés e infusiones": "☕",
    "Licores y carajillos": "🥃",
    "Bocadillos": "🥪",
    "Suplementos": "➕",
    "Lotería": "🎟️",
    "Bollería": "🥐",
    "Pan": "🍞",
    "Diadas": "🎉",
    "Gominolas y dulces": "🍬",
    "Pastelería": "🍰",
    "Menú": "🍽️",
    "Stock": "📦",
}
CATEGORIA_ICONO_DEFECTO = "🧺"

TURNOS = ("mañana", "tarde")
TURNO_LABELS = {
    "mañana": "Mañana",
    "tarde": "Tarde",
}


def get_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            categoria TEXT,
            precio_venta REAL,
            coste REAL,
            unidad TEXT DEFAULT 'ud',
            activo INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS movimientos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id INTEGER,
            producto_nombre TEXT NOT NULL,
            tipo TEXT NOT NULL,
            cantidad REAL NOT NULL,
            valor_unitario REAL,
            valor_total REAL,
            motivo TEXT,
            fecha TEXT NOT NULL,
            creado TEXT NOT NULL,
            lote TEXT,
            FOREIGN KEY(producto_id) REFERENCES productos(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS empleadas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            activo INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS turnos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            abierto_en TEXT NOT NULL,
            abierto_por TEXT,
            cerrado_en TEXT,
            cerrado_por TEXT,
            email_enviado INTEGER DEFAULT 0
        );

        CREATE INDEX IF NOT EXISTS idx_movimientos_fecha ON movimientos(fecha);
        CREATE INDEX IF NOT EXISTS idx_movimientos_tipo ON movimientos(tipo);
        """
    )
    columnas = [r["name"] for r in conn.execute("PRAGMA table_info(movimientos)").fetchall()]
    if "lote" not in columnas:
        conn.execute("ALTER TABLE movimientos ADD COLUMN lote TEXT")
    if "empleada_id" not in columnas:
        conn.execute("ALTER TABLE movimientos ADD COLUMN empleada_id INTEGER")
    if "empleada_nombre" not in columnas:
        conn.execute("ALTER TABLE movimientos ADD COLUMN empleada_nombre TEXT")
    if "turno" not in columnas:
        conn.execute("ALTER TABLE movimientos ADD COLUMN turno TEXT")
    columnas_prod = [r["name"] for r in conn.execute("PRAGMA table_info(productos)").fetchall()]
    if "foto" not in columnas_prod:
        conn.execute("ALTER TABLE productos ADD COLUMN foto TEXT")
    # "Invitación" se eliminó como tipo — los movimientos antiguos pasan a "errores".
    conn.execute("UPDATE movimientos SET tipo='errores' WHERE tipo='invitacion'")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_movimientos_lote ON movimientos(lote)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_movimientos_empleada ON movimientos(empleada_id)")

    # Si es la primera vez que arranca la app, dejamos un turno abierto para no bloquear el registro.
    hay_turnos = conn.execute("SELECT COUNT(*) as n FROM turnos").fetchone()["n"]
    if hay_turnos == 0:
        conn.execute(
            "INSERT INTO turnos (abierto_en, abierto_por) VALUES (?, ?)",
            (datetime.now().isoformat(timespec="seconds"), None),
        )

    conn.commit()
    conn.close()


# ---------- productos ----------

def list_productos(solo_activos=True):
    conn = get_db()
    q = "SELECT * FROM productos"
    if solo_activos:
        q += " WHERE activo = 1"
    q += " ORDER BY nombre COLLATE NOCASE"
    rows = conn.execute(q).fetchall()
    conn.close()
    return rows


def get_producto(producto_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM productos WHERE id = ?", (producto_id,)).fetchone()
    conn.close()
    return row


def insert_producto(nombre, categoria=None, precio_venta=None, coste=None, unidad="ud", foto=None):
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO productos (nombre, categoria, precio_venta, coste, unidad, foto) VALUES (?, ?, ?, ?, ?, ?)",
        (nombre.strip(), categoria, precio_venta, coste, unidad or "ud", foto),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def update_producto(producto_id, nombre, categoria, precio_venta, coste, unidad, foto=None):
    conn = get_db()
    conn.execute(
        "UPDATE productos SET nombre=?, categoria=?, precio_venta=?, coste=?, unidad=? WHERE id=?",
        (nombre.strip(), categoria, precio_venta, coste, unidad or "ud", producto_id),
    )
    if foto is not None:
        conn.execute("UPDATE productos SET foto=? WHERE id=?", (foto, producto_id))
    conn.commit()
    conn.close()


def set_producto_activo(producto_id, activo):
    conn = get_db()
    conn.execute("UPDATE productos SET activo=? WHERE id=?", (1 if activo else 0, producto_id))
    conn.commit()
    conn.close()


def find_producto_by_nombre(nombre, solo_activos=False):
    conn = get_db()
    q = "SELECT * FROM productos WHERE nombre = ? COLLATE NOCASE"
    if solo_activos:
        q += " AND activo = 1"
    row = conn.execute(q, (nombre.strip(),)).fetchone()
    conn.close()
    return row


def upsert_producto_from_import(nombre, categoria=None, precio_venta=None, coste=None, unidad="ud", foto=None):
    """Inserta el producto si no existe activo (por nombre); si existe, actualiza los campos no vacíos.
    Solo busca entre productos activos: un producto archivado con el mismo nombre no se reutiliza ni
    se reactiva por sorpresa — se crea uno nuevo."""
    existing = find_producto_by_nombre(nombre, solo_activos=True)
    if existing:
        conn = get_db()
        conn.execute(
            """UPDATE productos SET
                categoria = COALESCE(?, categoria),
                precio_venta = COALESCE(?, precio_venta),
                coste = COALESCE(?, coste),
                unidad = COALESCE(?, unidad),
                foto = COALESCE(?, foto)
               WHERE id = ?""",
            (categoria, precio_venta, coste, unidad, foto, existing["id"]),
        )
        conn.commit()
        conn.close()
        return existing["id"], False
    else:
        new_id = insert_producto(nombre, categoria, precio_venta, coste, unidad or "ud", foto)
        return new_id, True


# ---------- empleadas ----------

def list_empleadas(solo_activas=True):
    conn = get_db()
    q = "SELECT * FROM empleadas"
    if solo_activas:
        q += " WHERE activo = 1"
    q += " ORDER BY nombre COLLATE NOCASE"
    rows = conn.execute(q).fetchall()
    conn.close()
    return rows


def get_empleada(empleada_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM empleadas WHERE id = ?", (empleada_id,)).fetchone()
    conn.close()
    return row


def insert_empleada(nombre):
    conn = get_db()
    cur = conn.execute("INSERT INTO empleadas (nombre) VALUES (?)", (nombre.strip(),))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def update_empleada(empleada_id, nombre):
    conn = get_db()
    conn.execute("UPDATE empleadas SET nombre=? WHERE id=?", (nombre.strip(), empleada_id))
    conn.commit()
    conn.close()


def set_empleada_activa(empleada_id, activo):
    conn = get_db()
    conn.execute("UPDATE empleadas SET activo=? WHERE id=?", (1 if activo else 0, empleada_id))
    conn.commit()
    conn.close()


# ---------- movimientos ----------

def insert_movimiento(producto_id, producto_nombre, tipo, cantidad, valor_unitario, motivo, fecha,
                       lote=None, empleada_id=None, empleada_nombre=None, turno=None):
    valor_total = None
    if valor_unitario is not None:
        valor_total = round(float(valor_unitario) * float(cantidad), 2)
    conn = get_db()
    conn.execute(
        """INSERT INTO movimientos
           (producto_id, producto_nombre, tipo, cantidad, valor_unitario, valor_total, motivo, fecha, creado,
            lote, empleada_id, empleada_nombre, turno)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            producto_id,
            producto_nombre,
            tipo,
            cantidad,
            valor_unitario,
            valor_total,
            motivo,
            fecha,
            datetime.now().isoformat(timespec="seconds"),
            lote,
            empleada_id,
            empleada_nombre,
            turno,
        ),
    )
    conn.commit()
    conn.close()


def get_movimiento(movimiento_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM movimientos WHERE id = ?", (movimiento_id,)).fetchone()
    conn.close()
    return row


def get_movimientos_por_lote(lote):
    conn = get_db()
    rows = conn.execute("SELECT * FROM movimientos WHERE lote = ?", (lote,)).fetchall()
    conn.close()
    return rows


def delete_movimiento(movimiento_id):
    conn = get_db()
    conn.execute("DELETE FROM movimientos WHERE id = ?", (movimiento_id,))
    conn.commit()
    conn.close()


def delete_movimientos_por_lote(lote):
    conn = get_db()
    conn.execute("DELETE FROM movimientos WHERE lote = ?", (lote,))
    conn.commit()
    conn.close()


def list_movimientos(fecha_desde=None, fecha_hasta=None, tipo=None, empleada_id=None):
    conn = get_db()
    q = "SELECT * FROM movimientos WHERE 1=1"
    params = []
    if fecha_desde:
        q += " AND fecha >= ?"
        params.append(fecha_desde)
    if fecha_hasta:
        q += " AND fecha <= ?"
        params.append(fecha_hasta)
    if tipo:
        q += " AND tipo = ?"
        params.append(tipo)
    if empleada_id:
        q += " AND empleada_id = ?"
        params.append(empleada_id)
    q += " ORDER BY fecha DESC, id DESC"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return rows


def totales_por_tipo(fecha_desde=None, fecha_hasta=None):
    conn = get_db()
    q = """SELECT tipo, COUNT(*) as n, COALESCE(SUM(valor_total), 0) as total
           FROM movimientos WHERE 1=1"""
    params = []
    if fecha_desde:
        q += " AND fecha >= ?"
        params.append(fecha_desde)
    if fecha_hasta:
        q += " AND fecha <= ?"
        params.append(fecha_hasta)
    q += " GROUP BY tipo"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    totales = {t: {"n": 0, "total": 0.0} for t in TIPOS}
    for r in rows:
        totales[r["tipo"]] = {"n": r["n"], "total": r["total"]}
    return totales


def totales_por_producto(fecha_desde=None, fecha_hasta=None, tipo=None):
    conn = get_db()
    q = """SELECT producto_nombre, tipo, COUNT(*) as n, COALESCE(SUM(cantidad),0) as cantidad,
                  COALESCE(SUM(valor_total), 0) as total
           FROM movimientos WHERE 1=1"""
    params = []
    if fecha_desde:
        q += " AND fecha >= ?"
        params.append(fecha_desde)
    if fecha_hasta:
        q += " AND fecha <= ?"
        params.append(fecha_hasta)
    if tipo:
        q += " AND tipo = ?"
        params.append(tipo)
    q += " GROUP BY producto_nombre, tipo ORDER BY total DESC"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return rows


def totales_por_empleada(fecha_desde=None, fecha_hasta=None, tipo=None):
    conn = get_db()
    q = """SELECT COALESCE(empleada_nombre, 'Sin asignar') as empleada_nombre, tipo,
                  COUNT(*) as n, COALESCE(SUM(cantidad),0) as cantidad,
                  COALESCE(SUM(valor_total), 0) as total
           FROM movimientos WHERE 1=1"""
    params = []
    if fecha_desde:
        q += " AND fecha >= ?"
        params.append(fecha_desde)
    if fecha_hasta:
        q += " AND fecha <= ?"
        params.append(fecha_hasta)
    if tipo:
        q += " AND tipo = ?"
        params.append(tipo)
    q += " GROUP BY empleada_nombre, tipo ORDER BY total DESC"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return rows


def totales_por_turno(fecha_desde=None, fecha_hasta=None, tipo=None):
    conn = get_db()
    q = """SELECT COALESCE(turno, 'Sin turno') as turno, tipo,
                  COUNT(*) as n, COALESCE(SUM(cantidad),0) as cantidad,
                  COALESCE(SUM(valor_total), 0) as total
           FROM movimientos WHERE 1=1"""
    params = []
    if fecha_desde:
        q += " AND fecha >= ?"
        params.append(fecha_desde)
    if fecha_hasta:
        q += " AND fecha <= ?"
        params.append(fecha_hasta)
    if tipo:
        q += " AND tipo = ?"
        params.append(tipo)
    q += " GROUP BY turno, tipo ORDER BY total DESC"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return rows


# ---------- turnos (apertura / cierre de caja) ----------

def get_turno_abierto():
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM turnos WHERE cerrado_en IS NULL ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return row


def abrir_turno(nombre):
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO turnos (abierto_en, abierto_por) VALUES (?, ?)",
        (datetime.now().isoformat(timespec="seconds"), nombre),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def cerrar_turno(turno_id, nombre, email_enviado):
    conn = get_db()
    conn.execute(
        "UPDATE turnos SET cerrado_en=?, cerrado_por=?, email_enviado=? WHERE id=?",
        (datetime.now().isoformat(timespec="seconds"), nombre, 1 if email_enviado else 0, turno_id),
    )
    conn.commit()
    conn.close()


def movimientos_del_turno(abierto_en, hasta=None):
    conn = get_db()
    q = "SELECT * FROM movimientos WHERE creado >= ?"
    params = [abierto_en]
    if hasta:
        q += " AND creado <= ?"
        params.append(hasta)
    q += " ORDER BY creado ASC"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return rows


def total_errores_desde(abierto_en):
    conn = get_db()
    row = conn.execute(
        "SELECT COALESCE(SUM(valor_total),0) as total, COUNT(*) as n "
        "FROM movimientos WHERE tipo='errores' AND creado >= ?",
        (abierto_en,),
    ).fetchone()
    conn.close()
    return row["total"], row["n"]


def eliminar_errores_desde(abierto_en, hasta=None):
    conn = get_db()
    q = "DELETE FROM movimientos WHERE tipo='errores' AND creado >= ?"
    params = [abierto_en]
    if hasta:
        q += " AND creado <= ?"
        params.append(hasta)
    conn.execute(q, params)
    conn.commit()
    conn.close()
