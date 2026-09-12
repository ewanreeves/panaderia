"""Lee un volcado (mysqldump) de la base de datos de GOTPV y extrae productos, precios,
categorías y fotos. Solo toca las tablas `articulos` y `categorias` — nunca clientes,
empleados, tickets ni facturas.
"""
import hashlib
import re

ESCAPES = {
    0x30: 0x00,  # \0
    0x6e: 0x0a,  # \n
    0x72: 0x0d,  # \r
    0x74: 0x09,  # \t
    0x5a: 0x1a,  # \Z
    0x62: 0x08,  # \b
    0x27: 0x27,  # \'
    0x22: 0x22,  # \"
    0x5c: 0x5c,  # \\
}

# Icono de "sin foto" que trae GOTPV por defecto (una cámara tachada) — si un producto
# apunta a esta imagen exacta, es que nunca se le asignó una foto real.
HASH_SIN_FOTO = "2a617fec1e91f2d8"

MAPA_CATEGORIAS = {
    "BEBIDAS": "Bebidas",
    "CAFES- INFUSIONES -CHOCOLATES": "Cafés e infusiones",
    "LICORES Y CARAJILLOS": "Licores y carajillos",
    "BOCADILLOS": "Bocadillos",
    "SUPLEMENTO": "Suplementos",
    "LOTERIA DE CATALUNYA": "Lotería",
    "BOLLERIA DULCE Y SALADA": "Bollería",
    "PAN": "Pan",
    "DIADAS": "Diadas",
    "GOMINOLAS Y DULCES": "Gominolas y dulces",
    "PASTELERIA": "Pastelería",
    "MENU": "Menú",
    "STOC": "Stock",
}

NOMBRES_IGNORADOS = {"sin determinar"}


class ErrorImportacionGOTPV(Exception):
    pass


def find_table_columns(data, table_name):
    marker = f"CREATE TABLE `{table_name}` (".encode()
    try:
        start = data.index(marker) + len(marker)
    except ValueError:
        raise ErrorImportacionGOTPV(f"No se encuentra la tabla `{table_name}` en el fichero")
    end = data.index(b"\n) ENGINE", start)
    block = data[start:end]
    cols = []
    for line in block.split(b"\n"):
        line = line.strip()
        m = re.match(rb"`([^`]+)`", line)
        if m:
            cols.append(m.group(1).decode("latin1"))
    return cols


def _parse_field(data, pos):
    if data[pos:pos + 1] == b"'":
        pos += 1
        buf = bytearray()
        while True:
            c = data[pos]
            if c == 0x5c:
                nxt = data[pos + 1]
                buf.append(ESCAPES.get(nxt, nxt))
                pos += 2
            elif c == 0x27:
                pos += 1
                if data[pos:pos + 1] == b"'":
                    buf.append(0x27)
                    pos += 1
                else:
                    break
            else:
                buf.append(c)
                pos += 1
        return bytes(buf), pos
    else:
        start = pos
        while data[pos:pos + 1] not in (b",", b")"):
            pos += 1
        return data[start:pos], pos


def parse_insert_rows(data, table_name):
    marker = f"INSERT INTO `{table_name}` VALUES ".encode()
    idx = 0
    rows = []
    while True:
        idx = data.find(marker, idx)
        if idx == -1:
            break
        pos = idx + len(marker)
        while True:
            while data[pos:pos + 1] in b" \n\r\t,":
                pos += 1
            if data[pos:pos + 1] == b";":
                pos += 1
                break
            if data[pos:pos + 1] != b"(":
                raise ErrorImportacionGOTPV(f"Formato inesperado en `{table_name}` (posición {pos})")
            pos += 1
            fields = []
            while True:
                while data[pos:pos + 1] in b" \n\r\t":
                    pos += 1
                field, pos = _parse_field(data, pos)
                fields.append(field)
                while data[pos:pos + 1] in b" \n\r\t":
                    pos += 1
                if data[pos:pos + 1] == b",":
                    pos += 1
                    continue
                elif data[pos:pos + 1] == b")":
                    pos += 1
                    break
                else:
                    raise ErrorImportacionGOTPV(f"Formato inesperado en `{table_name}` (posición {pos})")
            rows.append(fields)
        idx = pos
    return rows


def sniff_ext(b):
    if b[:2] == b"BM":
        return "bmp"
    if b[:3] == b"\xff\xd8\xff":
        return "jpg"
    if b[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if b[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    return None


def _to_float(b):
    s = b.decode("latin1").strip()
    if not s or s.upper() == "NULL":
        return None
    try:
        v = float(s)
    except ValueError:
        return None
    return v if v != 0 else None


def extraer_productos(data):
    """Devuelve una lista de dicts: nombre, categoria, pvp, coste, medida, imagen (bytes o None),
    imagen_ext ('bmp'/'jpg'/...). Ignora los artículos placeholder de GOTPV (p.ej. "SIN DETERMINAR")."""
    cols_cat = find_table_columns(data, "categorias")
    rows_cat = parse_insert_rows(data, "categorias")
    i_catid = cols_cat.index("idcat")
    i_catnom = cols_cat.index("nomcat")
    categorias = {r[i_catid].decode(): r[i_catnom].decode("utf-8", errors="replace") for r in rows_cat}

    cols_art = find_table_columns(data, "articulos")
    rows_art = parse_insert_rows(data, "articulos")
    idx = {c: cols_art.index(c) for c in [
        "descripcion", "categoria", "pvp", "costeproveedorsiniva",
        "baseimponibleproveedor", "medida", "imagen1",
    ]}

    productos = []
    for r in rows_art:
        nombre = r[idx["descripcion"]].decode("utf-8", errors="replace").strip()
        if not nombre or nombre.lower() in NOMBRES_IGNORADOS:
            continue
        cat_id = r[idx["categoria"]].decode()
        cat_raw = categorias.get(cat_id, f"Categoria {cat_id}")
        categoria = MAPA_CATEGORIAS.get(cat_raw.upper(), cat_raw.title())
        pvp = _to_float(r[idx["pvp"]])
        coste = _to_float(r[idx["costeproveedorsiniva"]]) or _to_float(r[idx["baseimponibleproveedor"]])
        medida = r[idx["medida"]].decode("utf-8", errors="replace").strip() or "ud"
        imagen1 = r[idx["imagen1"]]

        imagen, imagen_ext = None, None
        if imagen1:
            h = hashlib.sha1(imagen1).hexdigest()[:16]
            if h != HASH_SIN_FOTO:
                ext = sniff_ext(imagen1)
                if ext:
                    imagen, imagen_ext = imagen1, ext

        productos.append({
            "nombre": nombre,
            "categoria": categoria,
            "pvp": pvp,
            "coste": coste,
            "medida": medida,
            "imagen": imagen,
            "imagen_ext": imagen_ext,
        })
    return productos
