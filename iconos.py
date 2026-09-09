"""Asigna un emoji a cada producto según palabras clave en el nombre, a falta de foto real."""

ICONOS_PRODUCTO = [
    (["croissant"], "🥐"),
    (["napolitana", "chocolate"], "🍫"),
    (["palmera"], "🥨"),
    (["ensaimada"], "🌀"),
    (["barra", "chapata", "payés", "payes", "integral", "baguette", "pan"], "🥖"),
    (["tarta", "queso"], "🍰"),
    (["milhojas"], "🧁"),
    (["bizcocho"], "🍋"),
    (["empanada"], "🥟"),
    (["quiche"], "🥧"),
    (["bocadillo", "sandwich", "sándwich"], "🥪"),
    (["café", "cafe", "cortado", "capuchino", "latte"], "☕"),
    (["té", " te", "infusion", "infusión"], "🍵"),
    (["zumo", "naranja", "jugo"], "🧃"),
    (["agua"], "💧"),
    (["cerveza"], "🍺"),
    (["vino"], "🍷"),
    (["ensalada"], "🥗"),
    (["huevo", "tortilla"], "🍳"),
]


def icono_para_producto(nombre, categoria=None, iconos_categoria=None, defecto="🧺"):
    n = (nombre or "").lower()
    for claves, icono in ICONOS_PRODUCTO:
        if any(c in n for c in claves):
            return icono
    if iconos_categoria and categoria in iconos_categoria:
        return iconos_categoria[categoria]
    return defecto
