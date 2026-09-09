import re
import pandas as pd

# Campos que puede tener un producto en la app
CAMPOS_DESTINO = [
    ("nombre", "Nombre del producto", True),
    ("categoria", "Categoría", False),
    ("precio_venta", "Precio de venta", False),
    ("coste", "Coste", False),
    ("unidad", "Unidad (ud, kg...)", False),
]


def leer_fichero(path):
    """Lee un CSV o Excel y devuelve un DataFrame con todo como texto (para no perder formato)."""
    if str(path).lower().endswith((".xlsx", ".xls")):
        df = pd.read_excel(path, dtype=str)
    else:
        df = None
        for encoding in ("utf-8-sig", "latin-1"):
            try:
                df = pd.read_csv(path, sep=None, engine="python", dtype=str, encoding=encoding)
                break
            except Exception:
                continue
        if df is None:
            raise ValueError("No se ha podido leer el CSV (codificación/formato no reconocido)")
    df = df.fillna("")
    df.columns = [str(c).strip() for c in df.columns]
    return df


def parse_numero(valor):
    """Convierte '3,50 €' / '3.50' / '' en float o None."""
    if valor is None:
        return None
    s = str(valor).strip()
    if not s:
        return None
    s = re.sub(r"[^\d,.\-]", "", s)
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def sugerir_mapeo(columnas):
    """Intenta adivinar qué columna del fichero corresponde a cada campo, por nombre habitual."""
    alias = {
        "nombre": ["nombre", "producto", "articulo", "artículo", "descripcion", "descripción"],
        "categoria": ["categoria", "categoría", "familia", "grupo", "seccion", "sección"],
        "precio_venta": ["precio venta", "pvp", "precio", "precio de venta", "p.v.p."],
        "coste": ["coste", "costo", "precio compra", "precio coste", "coste unitario"],
        "unidad": ["unidad", "ud", "medida", "formato"],
    }
    cols_lower = {c.lower().strip(): c for c in columnas}
    mapeo = {}
    for campo, nombres in alias.items():
        encontrado = None
        for n in nombres:
            if n in cols_lower:
                encontrado = cols_lower[n]
                break
        if not encontrado:
            for col_lower, col_original in cols_lower.items():
                if any(n in col_lower for n in nombres):
                    encontrado = col_original
                    break
        mapeo[campo] = encontrado
    return mapeo
