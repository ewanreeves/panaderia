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
            apellidos TEXT,
            dni TEXT,
            horas_semanales REAL,
            activo INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS fichajes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empleada_id INTEGER NOT NULL,
            empleada_nombre TEXT NOT NULL,
            entrada TEXT NOT NULL,
            salida TEXT,
            FOREIGN KEY(empleada_id) REFERENCES empleadas(id)
        );

        CREATE TABLE IF NOT EXISTS stock_movimientos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            creado TEXT NOT NULL,
            producto_id INTEGER NOT NULL,
            producto_nombre TEXT NOT NULL,
            tipo TEXT NOT NULL,
            delta REAL NOT NULL,
            resultante REAL NOT NULL,
            empleada_nombre TEXT,
            movimiento_id INTEGER
        );

        CREATE INDEX IF NOT EXISTS idx_stock_fecha ON stock_movimientos(fecha);
        CREATE INDEX IF NOT EXISTS idx_stock_movimiento ON stock_movimientos(movimiento_id);

        CREATE TABLE IF NOT EXISTS turnos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            abierto_en TEXT NOT NULL,
            abierto_por TEXT,
            cerrado_en TEXT,
            cerrado_por TEXT,
            email_enviado INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS configuracion (
            clave TEXT PRIMARY KEY,
            valor TEXT
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
    columnas_emp = [r["name"] for r in conn.execute("PRAGMA table_info(empleadas)").fetchall()]
    if "apellidos" not in columnas_emp:
        conn.execute("ALTER TABLE empleadas ADD COLUMN apellidos TEXT")
    if "dni" not in columnas_emp:
        conn.execute("ALTER TABLE empleadas ADD COLUMN dni TEXT")
    if "horas_semanales" not in columnas_emp:
        conn.execute("ALTER TABLE empleadas ADD COLUMN horas_semanales REAL")
    columnas_fichajes = [r["name"] for r in conn.execute("PRAGMA table_info(fichajes)").fetchall()]
    if "editado_motivo" not in columnas_fichajes:
        conn.execute("ALTER TABLE fichajes ADD COLUMN editado_motivo TEXT")
    if "editado_en" not in columnas_fichajes:
        conn.execute("ALTER TABLE fichajes ADD COLUMN editado_en TEXT")
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


def insert_empleada(nombre, apellidos=None, dni=None, horas_semanales=None):
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO empleadas (nombre, apellidos, dni, horas_semanales) VALUES (?, ?, ?, ?)",
        (nombre.strip(), apellidos, dni, horas_semanales),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def update_empleada(empleada_id, nombre, apellidos=None, dni=None, horas_semanales=None):
    conn = get_db()
    conn.execute(
        "UPDATE empleadas SET nombre=?, apellidos=?, dni=?, horas_semanales=? WHERE id=?",
        (nombre.strip(), apellidos, dni, horas_semanales, empleada_id),
    )
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
    cur = conn.execute(
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
    nuevo_id = cur.lastrowid
    conn.close()
    return nuevo_id


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
    # Si el movimiento había descontado stock, al borrarlo el stock se recupera.
    conn.execute("DELETE FROM stock_movimientos WHERE movimiento_id = ?", (movimiento_id,))
    conn.execute("DELETE FROM movimientos WHERE id = ?", (movimiento_id,))
    conn.commit()
    conn.close()


def delete_movimientos_por_lote(lote):
    conn = get_db()
    conn.execute(
        "DELETE FROM stock_movimientos WHERE movimiento_id IN (SELECT id FROM movimientos WHERE lote = ?)",
        (lote,),
    )
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


# ---------- configuración (ajustable desde la app, sin tocar config.py) ----------

def get_config(clave, defecto=None):
    conn = get_db()
    row = conn.execute("SELECT valor FROM configuracion WHERE clave = ?", (clave,)).fetchone()
    conn.close()
    if row is None or row["valor"] in (None, ""):
        return defecto
    return row["valor"]


def set_config(clave, valor):
    conn = get_db()
    conn.execute(
        "INSERT INTO configuracion (clave, valor) VALUES (?, ?) "
        "ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor",
        (clave, valor),
    )
    conn.commit()
    conn.close()


# ---------- fichajes (control de horas) ----------

def get_fichaje_abierto(empleada_id):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM fichajes WHERE empleada_id = ? AND salida IS NULL ORDER BY id DESC LIMIT 1",
        (empleada_id,),
    ).fetchone()
    conn.close()
    return row


def fichajes_activos():
    """Todo el mundo que está fichada ahora mismo (sin salida registrada)."""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM fichajes WHERE salida IS NULL ORDER BY entrada ASC"
    ).fetchall()
    conn.close()
    return rows


def fichar_entrada(empleada_id, empleada_nombre):
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO fichajes (empleada_id, empleada_nombre, entrada) VALUES (?, ?, ?)",
        (empleada_id, empleada_nombre, datetime.now().isoformat(timespec="seconds")),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def fichar_salida(fichaje_id):
    conn = get_db()
    conn.execute(
        "UPDATE fichajes SET salida=? WHERE id=?",
        (datetime.now().isoformat(timespec="seconds"), fichaje_id),
    )
    conn.commit()
    conn.close()


def fichajes_del_turno(abierto_en, hasta=None):
    """Fichajes cuya entrada cae dentro de la ventana del turno (igual criterio que los movimientos)."""
    conn = get_db()
    q = "SELECT * FROM fichajes WHERE entrada >= ?"
    params = [abierto_en]
    if hasta:
        q += " AND entrada <= ?"
        params.append(hasta)
    q += " ORDER BY entrada ASC"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return rows


def fichajes_rango(desde_iso, hasta_iso, empleada_id=None):
    conn = get_db()
    q = "SELECT * FROM fichajes WHERE entrada >= ? AND entrada <= ?"
    params = [desde_iso, hasta_iso]
    if empleada_id:
        q += " AND empleada_id = ?"
        params.append(empleada_id)
    q += " ORDER BY entrada ASC"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return rows


def get_fichaje(fichaje_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM fichajes WHERE id = ?", (fichaje_id,)).fetchone()
    conn.close()
    return row


def insert_fichaje_manual(empleada_id, empleada_nombre, entrada_iso, salida_iso, motivo):
    """Alta manual de un fichaje olvidado (ej. se le pasó fichar la entrada). Queda marcado como
    corrección, con el motivo, para que el registro siga siendo transparente."""
    conn = get_db()
    cur = conn.execute(
        """INSERT INTO fichajes (empleada_id, empleada_nombre, entrada, salida, editado_motivo, editado_en)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (empleada_id, empleada_nombre, entrada_iso, salida_iso, motivo,
         datetime.now().isoformat(timespec="seconds")),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def update_fichaje(fichaje_id, entrada_iso, salida_iso, motivo):
    """Corrige entrada/salida de un fichaje ya existente (ej. no marcó un descanso o fue al
    médico). El motivo queda guardado junto con la fecha de la corrección — no se sobrescribe
    en silencio."""
    conn = get_db()
    conn.execute(
        "UPDATE fichajes SET entrada=?, salida=?, editado_motivo=?, editado_en=? WHERE id=?",
        (entrada_iso, salida_iso, motivo, datetime.now().isoformat(timespec="seconds"), fichaje_id),
    )
    conn.commit()
    conn.close()


def delete_fichaje(fichaje_id):
    conn = get_db()
    conn.execute("DELETE FROM fichajes WHERE id = ?", (fichaje_id,))
    conn.commit()
    conn.close()


# ---------- stock del día ----------
#
# El stock de un producto es la suma de sus cambios (stock_movimientos) del día. Como cada
# consulta filtra por fecha, al llegar el día siguiente el stock vuelve a ser 0 solo, sin
# ninguna tarea de "reinicio": hay que volver a meterlo a mano por la mañana. Los cambios
# de días anteriores se conservan como histórico.

TIPOS_STOCK_DESCUENTAN = ("merma", "reciclaje", "autoconsumo")


def stock_actual(fecha):
    """{producto_id: cantidad} de los productos que tienen stock declarado en esa fecha."""
    conn = get_db()
    rows = conn.execute(
        "SELECT producto_id, SUM(delta) AS cantidad FROM stock_movimientos WHERE fecha = ? GROUP BY producto_id",
        (fecha,),
    ).fetchall()
    conn.close()
    return {r["producto_id"]: round(r["cantidad"], 4) for r in rows}


def stock_fijar(fecha, producto_id, producto_nombre, nueva_cantidad, empleada_nombre):
    """Deja el stock del producto en `nueva_cantidad`. La primera vez del día cuenta como stock
    inicial; las siguientes, como ajuste manual. Devuelve False si no cambia nada."""
    conn = get_db()
    row = conn.execute(
        "SELECT COUNT(*) AS n, COALESCE(SUM(delta), 0) AS actual FROM stock_movimientos "
        "WHERE fecha = ? AND producto_id = ?",
        (fecha, producto_id),
    ).fetchone()
    hay_previo = row["n"] > 0
    actual = row["actual"]
    if hay_previo and abs(nueva_cantidad - actual) < 1e-9:
        conn.close()
        return False
    conn.execute(
        """INSERT INTO stock_movimientos
           (fecha, creado, producto_id, producto_nombre, tipo, delta, resultante, empleada_nombre)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (fecha, datetime.now().isoformat(timespec="seconds"), producto_id, producto_nombre,
         "ajuste" if hay_previo else "inicial", nueva_cantidad - actual, nueva_cantidad, empleada_nombre),
    )
    conn.commit()
    conn.close()
    return True


def stock_descontar(fecha, producto_id, producto_nombre, cantidad, tipo, empleada_nombre, movimiento_id):
    """Resta del stock del día lo que se ha registrado como merma/reciclaje/autoconsumo. Solo si
    ese producto tiene stock declarado hoy (si nadie lo ha contado, no hay nada que descontar).
    Devuelve el stock resultante, o None si no se ha descontado."""
    conn = get_db()
    row = conn.execute(
        "SELECT COUNT(*) AS n, COALESCE(SUM(delta), 0) AS actual FROM stock_movimientos "
        "WHERE fecha = ? AND producto_id = ?",
        (fecha, producto_id),
    ).fetchone()
    if row["n"] == 0:
        conn.close()
        return None
    resultante = row["actual"] - cantidad
    conn.execute(
        """INSERT INTO stock_movimientos
           (fecha, creado, producto_id, producto_nombre, tipo, delta, resultante, empleada_nombre, movimiento_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (fecha, datetime.now().isoformat(timespec="seconds"), producto_id, producto_nombre,
         tipo, -cantidad, resultante, empleada_nombre, movimiento_id),
    )
    conn.commit()
    conn.close()
    return resultante


def stock_movimientos_dia(fecha):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM stock_movimientos WHERE fecha = ? ORDER BY id ASC", (fecha,)
    ).fetchall()
    conn.close()
    return rows


def stock_resumen_dia(fecha):
    """Una fila por producto con stock hoy: inicial, ajustes manuales, lo descontado por cada
    tipo de movimiento y el stock actual. Ordenado por nombre."""
    resumen = {}
    for m in stock_movimientos_dia(fecha):
        r = resumen.setdefault(m["producto_id"], {
            "producto_id": m["producto_id"], "producto_nombre": m["producto_nombre"],
            "inicial": 0.0, "ajustes": 0.0, "merma": 0.0, "reciclaje": 0.0, "autoconsumo": 0.0,
            "actual": 0.0,
        })
        if m["tipo"] == "inicial":
            r["inicial"] += m["delta"]
        elif m["tipo"] == "ajuste":
            r["ajustes"] += m["delta"]
        elif m["tipo"] in TIPOS_STOCK_DESCUENTAN:
            r[m["tipo"]] += -m["delta"]
        r["actual"] += m["delta"]
    return sorted(resumen.values(), key=lambda r: r["producto_nombre"].lower())


# ---------- borrado de datos de demo ----------

def borrar_datos_demo():
    """Borra movimientos, stock, fichajes, turnos y personal. No toca productos ni configuracion.
    Deja un turno recién abierto para que la app siga usable justo después del borrado."""
    conn = get_db()
    conn.execute("DELETE FROM stock_movimientos")
    conn.execute("DELETE FROM movimientos")
    conn.execute("DELETE FROM fichajes")
    conn.execute("DELETE FROM turnos")
    conn.execute("DELETE FROM empleadas")
    conn.execute(
        "INSERT INTO turnos (abierto_en, abierto_por) VALUES (?, ?)",
        (datetime.now().isoformat(timespec="seconds"), None),
    )
    conn.commit()
    conn.close()
