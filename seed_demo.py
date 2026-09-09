"""Rellena la base de datos con un catálogo y movimientos de ejemplo para hacer demos.
Uso: venv\\Scripts\\python.exe seed_demo.py
"""
from datetime import date, timedelta

import database as db

PRODUCTOS_DEMO = [
    # nombre, categoria, precio_venta, coste, unidad
    ("Barra de pan", "Panadería", 0.90, 0.20, "ud"),
    ("Pan integral", "Panadería", 1.20, 0.30, "ud"),
    ("Chapata", "Panadería", 1.00, 0.25, "ud"),
    ("Pan de payés", "Panadería", 2.80, 0.70, "ud"),
    ("Croissant", "Bollería", 1.30, 0.35, "ud"),
    ("Napolitana de chocolate", "Bollería", 1.50, 0.40, "ud"),
    ("Palmera", "Bollería", 1.60, 0.45, "ud"),
    ("Ensaimada", "Bollería", 2.20, 0.60, "ud"),
    ("Tarta de queso", "Pastelería", 3.50, 1.00, "porción"),
    ("Milhojas", "Pastelería", 2.80, 0.80, "ud"),
    ("Bizcocho de limón", "Pastelería", 2.50, 0.70, "porción"),
    ("Empanada", "Salados", 2.20, 0.70, "ud"),
    ("Bocadillo de jamón", "Salados", 3.50, 1.20, "ud"),
    ("Quiche de verduras", "Salados", 3.00, 1.00, "porción"),
    ("Café con leche", "Bebidas", 1.60, 0.30, "ud"),
    ("Cortado", "Bebidas", 1.40, 0.25, "ud"),
    ("Té", "Bebidas", 1.50, 0.25, "ud"),
    ("Zumo de naranja", "Bebidas", 2.50, 0.80, "ud"),
    ("Agua", "Bebidas", 1.20, 0.25, "ud"),
]

MOVIMIENTOS_DEMO = [
    # días atrás, tipo, nombre producto, cantidad, motivo
    (0, "merma", "Napolitana de chocolate", 2, "sobras del día, caducadas"),
    (0, "autoconsumo", "Café con leche", 2, "desayuno del personal"),
    (0, "reciclaje", "Croissant", 3, "del día anterior, aprovechado para tostadas"),
    (1, "merma", "Barra de pan", 3, "no vendido, se pone duro"),
    (1, "autoconsumo", "Bocadillo de jamón", 1, "comida del personal"),
    (2, "merma", "Milhojas", 1, "roto en el escaparate"),
    (2, "errores", "Café con leche", 1, "cobrado por error, no se sirvió"),
    (3, "merma", "Ensaimada", 2, "sobras del fin de semana"),
    (3, "autoconsumo", "Agua", 4, "personal, turno de tarde"),
    (4, "reciclaje", "Tarta de queso", 1, "recortes aprovechados en otra elaboración"),
    (5, "merma", "Empanada", 1, "caducada"),
    (6, "merma", "Chapata", 2, "no vendido"),
    (6, "autoconsumo", "Cortado", 1, "desayuno del personal"),
]


def main():
    db.init_db()

    ids = {}
    for nombre, categoria, precio, coste, unidad in PRODUCTOS_DEMO:
        producto_id, _ = db.upsert_producto_from_import(nombre, categoria, precio, coste, unidad)
        ids[nombre] = producto_id
    print(f"Catálogo demo: {len(PRODUCTOS_DEMO)} productos")

    for dias_atras, tipo, nombre, cantidad, motivo in MOVIMIENTOS_DEMO:
        producto = db.get_producto(ids[nombre])
        if tipo == "errores":
            valor_unitario = producto["precio_venta"]
        else:
            valor_unitario = producto["coste"]
        fecha = (date.today() - timedelta(days=dias_atras)).isoformat()
        db.insert_movimiento(
            producto_id=producto["id"],
            producto_nombre=producto["nombre"],
            tipo=tipo,
            cantidad=cantidad,
            valor_unitario=valor_unitario,
            motivo=motivo,
            fecha=fecha,
        )
    print(f"Movimientos demo: {len(MOVIMIENTOS_DEMO)} registrados")


if __name__ == "__main__":
    main()
