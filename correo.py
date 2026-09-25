import io
import smtplib
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

import config
import database as db


def ajustes_smtp():
    """Los ajustes configurados desde la app (tabla configuracion) mandan sobre config.py."""
    return {
        "host": db.get_config("smtp_host", config.SMTP_HOST),
        "port": int(db.get_config("smtp_port", config.SMTP_PORT)),
        "user": db.get_config("smtp_user", config.SMTP_USER),
        "password": db.get_config("smtp_password", config.SMTP_PASSWORD),
        "destino": db.get_config("email_destino", config.EMAIL_DESTINO),
    }


def horas_entre(entrada_iso, salida_iso):
    """Horas reales entre dos marcas ISO. Sin retoques: si no hay salida, se calcula hasta
    ahora y se marca como en curso — nunca se recorta ni se redondea al alza ni a la baja."""
    inicio = datetime.fromisoformat(entrada_iso)
    if salida_iso:
        fin = datetime.fromisoformat(salida_iso)
        en_curso = False
    else:
        fin = datetime.now()
        en_curso = True
    horas = (fin - inicio).total_seconds() / 3600
    return round(horas, 2), en_curso


def _fichajes_html(fichajes):
    if not fichajes:
        return "<p><i>Nadie fichó entrada durante este turno.</i></p>"
    filas = []
    total_horas = 0.0
    for f in fichajes:
        horas, en_curso = horas_entre(f["entrada"], f["salida"])
        total_horas += horas
        salida_txt = f["salida"][11:16] if f["salida"] else "— (sigue fichada)"
        filas.append(
            f"<tr><td>{f['empleada_nombre']}</td><td>{f['entrada'][11:16]}</td>"
            f"<td>{salida_txt}</td><td>{horas:.2f} h</td></tr>"
        )
    return f"""
    <table border="1" cellpadding="4" cellspacing="0">
      <tr><th>Personal</th><th>Entrada</th><th>Salida</th><th>Horas</th></tr>
      {''.join(filas)}
    </table>
    <p><b>Total horas fichadas:</b> {total_horas:.2f} h</p>
    """


def _num(valor):
    texto = f"{valor:.2f}".rstrip("0").rstrip(".")
    return texto.replace(".", ",") if texto not in ("", "-0") else "0"


def _stock_html(stock):
    if not stock or not stock["movimientos"]:
        return "<p><i>Hoy no se ha declarado stock.</i></p>"
    filas = "".join(
        f"<tr><td>{r['producto_nombre']}</td><td>{_num(r['inicial'])}</td><td>{_num(r['ajustes'])}</td>"
        f"<td>{_num(r['merma'])}</td><td>{_num(r['reciclaje'])}</td><td>{_num(r['autoconsumo'])}</td>"
        f"<td><b>{_num(r['actual'])}</b></td></tr>"
        for r in stock["resumen"]
    )
    detalle = "".join(
        f"<tr><td>{m['creado'][11:16]}</td><td>{m['producto_nombre']}</td>"
        f"<td>{STOCK_TIPO_LABELS.get(m['tipo'], m['tipo'])}</td><td>{_num(m['delta'])}</td>"
        f"<td>{_num(m['resultante'])}</td><td>{m['empleada_nombre'] or ''}</td></tr>"
        for m in stock["movimientos"]
    )
    return f"""
    <p>Stock del día {stock['fecha']} (mañana empieza otra vez en 0):</p>
    <table border="1" cellpadding="4" cellspacing="0">
      <tr><th>Producto</th><th>Inicial</th><th>Ajustes a mano</th><th>Merma</th><th>Reciclaje</th>
          <th>Autoconsumo</th><th>Stock ahora</th></tr>
      {filas}
    </table>
    <p>Todos los movimientos de stock del día:</p>
    <table border="1" cellpadding="4" cellspacing="0">
      <tr><th>Hora</th><th>Producto</th><th>Tipo</th><th>Cambio</th><th>Resultado</th><th>Personal</th></tr>
      {detalle}
    </table>
    """


STOCK_TIPO_LABELS = {
    "inicial": "Stock inicial",
    "ajuste": "Ajuste a mano",
    "merma": "Merma",
    "reciclaje": "Reciclaje",
    "autoconsumo": "Autoconsumo",
}


def construir_informe_html(turno, movimientos, totales_tipo, admin_nombre, fichajes=None, stock=None):
    filas = "".join(
        f"<tr><td>{m['fecha']}</td><td>{db.TIPO_LABELS.get(m['tipo'], m['tipo'])}</td>"
        f"<td>{m['producto_nombre']}</td><td>{m['cantidad']}</td>"
        f"<td>{'%.2f' % m['valor_total'] if m['valor_total'] is not None else '—'} €</td>"
        f"<td>{m['empleada_nombre'] or ''}</td><td>{m['motivo'] or ''}</td></tr>"
        for m in movimientos
    )
    resumen = "".join(
        f"<li><b>{db.TIPO_LABELS.get(t, t)}</b>: {totales_tipo[t]['n']} movimientos, "
        f"{'%.2f' % totales_tipo[t]['total']} €</li>"
        for t in db.TIPOS
    )
    cerrado_por = turno["cerrado_por"] or admin_nombre
    return f"""
    <h2>Cierre de turno — {cerrado_por}</h2>
    <p>Abierto: {turno['abierto_en']}<br>Cerrado: {turno['cerrado_en']}</p>
    <ul>{resumen}</ul>
    <p><i>Los movimientos de tipo "Errores" se han eliminado tras este envío y no aparecen en Informes.</i></p>
    <p>Se adjunta el detalle completo en Excel.</p>
    <h3>Personal — entrada y salida</h3>
    {_fichajes_html(fichajes or [])}
    <h3>Stock</h3>
    {_stock_html(stock)}
    <h3>Movimientos del turno</h3>
    <table border="1" cellpadding="4" cellspacing="0">
      <tr><th>Fecha</th><th>Tipo</th><th>Producto</th><th>Cant.</th><th>Valor</th><th>Personal</th><th>Motivo</th></tr>
      {filas}
    </table>
    """


CABECERA_FILL = PatternFill(start_color="F3E9D8", end_color="F3E9D8", fill_type="solid")
CABECERA_FONT = Font(bold=True)
EUROS = '#,##0.00 "€"'
BASE_VALOR = {t: ("Precio de venta" if t == "errores" else "Coste") for t in db.TIPOS}


def _autoajustar(ws, anchos):
    for i, ancho in enumerate(anchos, start=1):
        ws.column_dimensions[get_column_letter(i)].width = ancho


def _cabecera(ws, fila, textos):
    for col, texto in enumerate(textos, start=1):
        c = ws.cell(row=fila, column=col, value=texto)
        c.font = CABECERA_FONT
        c.fill = CABECERA_FILL
        c.alignment = Alignment(horizontal="left")


def _agrupar(movimientos, clave_fn):
    """Agrupa por (clave, tipo) y devuelve [(clave, tipo, cantidad, n, total), ...] ordenado por valor."""
    grupos = {}
    orden = []
    for m in movimientos:
        clave = (clave_fn(m), m["tipo"])
        if clave not in grupos:
            grupos[clave] = {"cantidad": 0, "n": 0, "total": 0.0}
            orden.append(clave)
        g = grupos[clave]
        g["cantidad"] += m["cantidad"] or 0
        g["n"] += 1
        g["total"] += m["valor_total"] or 0
    orden.sort(key=lambda c: -grupos[c]["total"])
    return [(c[0], c[1], grupos[c]) for c in orden]


def _hoja_resumen(wb, turno, totales_tipo, admin_nombre):
    ws = wb.active
    ws.title = "Resumen"
    ws["A1"] = "Cierre de turno"
    ws["A1"].font = Font(bold=True, size=14)
    ws["A2"] = "Cerrado por"
    ws["B2"] = turno["cerrado_por"] or admin_nombre
    ws["A3"] = "Abierto"
    ws["B3"] = turno["abierto_en"]
    ws["A4"] = "Cerrado"
    ws["B4"] = turno["cerrado_en"]

    fila = 6
    _cabecera(ws, fila, ["Concepto", "Nº movimientos", "Valor total", "Valorado a"])
    total_general = 0.0
    for t in db.TIPOS:
        fila += 1
        ws.cell(row=fila, column=1, value=db.TIPO_LABELS.get(t, t))
        ws.cell(row=fila, column=2, value=totales_tipo[t]["n"])
        celda_valor = ws.cell(row=fila, column=3, value=totales_tipo[t]["total"])
        celda_valor.number_format = EUROS
        ws.cell(row=fila, column=4, value=BASE_VALOR[t])
        total_general += totales_tipo[t]["total"]
    fila += 1
    ws.cell(row=fila, column=1, value="Total").font = Font(bold=True)
    celda_total = ws.cell(row=fila, column=3, value=total_general)
    celda_total.font = Font(bold=True)
    celda_total.number_format = EUROS

    fila += 3
    ws.cell(row=fila, column=1, value=(
        'Los movimientos de "Errores" se borran de la app tras este cierre — esta hoja y la pestaña '
        '"Errores" son el único registro que queda de ellos.'
    )).font = Font(italic=True, color="8B7C68")
    ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=4)
    _autoajustar(ws, [16, 16, 14, 16])


def _hoja_tipo(wb, tipo, movimientos_tipo):
    ws = wb.create_sheet(db.TIPO_LABELS.get(tipo, tipo))
    ws["A1"] = f"Valorado a: {BASE_VALOR[tipo]}"
    ws["A1"].font = Font(italic=True, color="8B7C68")

    cabeceras = ["Fecha", "Producto", "Cantidad", "Valor unitario", "Valor total", "Personal", "Turno", "Motivo"]
    fila_cab = 3
    _cabecera(ws, fila_cab, cabeceras)
    ws.freeze_panes = f"A{fila_cab + 1}"

    fila = fila_cab
    total = 0.0
    for m in movimientos_tipo:
        fila += 1
        ws.cell(row=fila, column=1, value=m["fecha"])
        ws.cell(row=fila, column=2, value=m["producto_nombre"])
        ws.cell(row=fila, column=3, value=m["cantidad"])
        if m["valor_unitario"] is not None:
            ws.cell(row=fila, column=4, value=m["valor_unitario"]).number_format = EUROS
        if m["valor_total"] is not None:
            ws.cell(row=fila, column=5, value=m["valor_total"]).number_format = EUROS
            total += m["valor_total"]
        ws.cell(row=fila, column=6, value=m["empleada_nombre"] or "")
        ws.cell(row=fila, column=7, value=db.TURNO_LABELS.get(m["turno"], m["turno"] or ""))
        ws.cell(row=fila, column=8, value=m["motivo"] or "")

    if not movimientos_tipo:
        ws.cell(row=fila_cab + 1, column=1, value="Sin movimientos en este turno").font = Font(italic=True)
    else:
        fila += 1
        ws.cell(row=fila, column=1, value="Total").font = Font(bold=True)
        c = ws.cell(row=fila, column=5, value=total)
        c.font = Font(bold=True)
        c.number_format = EUROS

    _autoajustar(ws, [12, 30, 10, 14, 14, 16, 10, 30])


def _hoja_agrupada(wb, nombre, titulo_columna, grupos):
    ws = wb.create_sheet(nombre)
    _cabecera(ws, 1, [titulo_columna, "Concepto", "Cantidad", "Nº movimientos", "Valor total"])
    ws.freeze_panes = "A2"
    fila = 1
    for clave, tipo, datos in grupos:
        fila += 1
        ws.cell(row=fila, column=1, value=clave)
        ws.cell(row=fila, column=2, value=db.TIPO_LABELS.get(tipo, tipo))
        ws.cell(row=fila, column=3, value=datos["cantidad"])
        ws.cell(row=fila, column=4, value=datos["n"])
        ws.cell(row=fila, column=5, value=datos["total"]).number_format = EUROS
    if fila == 1:
        ws.cell(row=2, column=1, value="Sin movimientos en este turno").font = Font(italic=True)
    _autoajustar(ws, [26, 16, 12, 14, 14])


def _hoja_fichajes(wb, fichajes):
    ws = wb.create_sheet("Personal - horas")
    _cabecera(ws, 1, ["Personal", "Entrada", "Salida", "Horas trabajadas"])
    ws.freeze_panes = "A2"
    fila = 1
    total = 0.0
    for f in fichajes:
        fila += 1
        horas, en_curso = horas_entre(f["entrada"], f["salida"])
        total += horas
        ws.cell(row=fila, column=1, value=f["empleada_nombre"])
        ws.cell(row=fila, column=2, value=f["entrada"])
        ws.cell(row=fila, column=3, value=f["salida"] or "Sigue fichada")
        ws.cell(row=fila, column=4, value=horas)
    if fila == 1:
        ws.cell(row=2, column=1, value="Nadie fichó entrada en este turno").font = Font(italic=True)
    else:
        fila += 1
        ws.cell(row=fila, column=1, value="Total horas").font = Font(bold=True)
        ws.cell(row=fila, column=4, value=round(total, 2)).font = Font(bold=True)
    _autoajustar(ws, [22, 20, 20, 18])


def _hoja_stock(wb, stock):
    ws = wb.create_sheet("Stock")
    _cabecera(ws, 1, ["Producto", "Inicial", "Ajustes a mano", "Merma", "Reciclaje", "Autoconsumo", "Stock ahora"])
    ws.freeze_panes = "A2"
    resumen = stock["resumen"] if stock else []
    for fila, r in enumerate(resumen, start=2):
        ws.cell(row=fila, column=1, value=r["producto_nombre"])
        for col, clave in enumerate(["inicial", "ajustes", "merma", "reciclaje", "autoconsumo", "actual"], start=2):
            ws.cell(row=fila, column=col, value=r[clave])
        ws.cell(row=fila, column=7).font = Font(bold=True)
    if not resumen:
        ws.cell(row=2, column=1, value="Hoy no se ha declarado stock").font = Font(italic=True)
    _autoajustar(ws, [30, 10, 16, 10, 12, 14, 12])

    ws2 = wb.create_sheet("Stock - movimientos")
    _cabecera(ws2, 1, ["Fecha", "Hora", "Producto", "Tipo", "Cambio", "Resultado", "Personal"])
    ws2.freeze_panes = "A2"
    movimientos = stock["movimientos"] if stock else []
    for fila, m in enumerate(movimientos, start=2):
        ws2.cell(row=fila, column=1, value=m["fecha"])
        ws2.cell(row=fila, column=2, value=m["creado"][11:16])
        ws2.cell(row=fila, column=3, value=m["producto_nombre"])
        ws2.cell(row=fila, column=4, value=STOCK_TIPO_LABELS.get(m["tipo"], m["tipo"]))
        ws2.cell(row=fila, column=5, value=m["delta"])
        ws2.cell(row=fila, column=6, value=m["resultante"])
        ws2.cell(row=fila, column=7, value=m["empleada_nombre"] or "")
    if not movimientos:
        ws2.cell(row=2, column=1, value="Hoy no se ha declarado stock").font = Font(italic=True)
    _autoajustar(ws2, [12, 8, 30, 16, 10, 12, 16])


def _hoja_todo(wb, movimientos):
    ws = wb.create_sheet("Detalle completo")
    cabeceras = ["Fecha", "Concepto", "Producto", "Cantidad", "Valorado a", "Valor unitario",
                 "Valor total", "Personal", "Turno", "Motivo"]
    _cabecera(ws, 1, cabeceras)
    ws.freeze_panes = "A2"
    for fila, m in enumerate(movimientos, start=2):
        ws.cell(row=fila, column=1, value=m["fecha"])
        ws.cell(row=fila, column=2, value=db.TIPO_LABELS.get(m["tipo"], m["tipo"]))
        ws.cell(row=fila, column=3, value=m["producto_nombre"])
        ws.cell(row=fila, column=4, value=m["cantidad"])
        ws.cell(row=fila, column=5, value=BASE_VALOR.get(m["tipo"], ""))
        if m["valor_unitario"] is not None:
            ws.cell(row=fila, column=6, value=m["valor_unitario"]).number_format = EUROS
        if m["valor_total"] is not None:
            ws.cell(row=fila, column=7, value=m["valor_total"]).number_format = EUROS
        ws.cell(row=fila, column=8, value=m["empleada_nombre"] or "")
        ws.cell(row=fila, column=9, value=db.TURNO_LABELS.get(m["turno"], m["turno"] or ""))
        ws.cell(row=fila, column=10, value=m["motivo"] or "")
    _autoajustar(ws, [12, 14, 30, 10, 15, 14, 14, 16, 10, 30])


def construir_excel_informe(turno, movimientos, totales_tipo, admin_nombre, fichajes=None, stock=None):
    """Devuelve un BytesIO con el .xlsx: resumen, horas del personal, stock del día, una pestaña
    por concepto (con su subtotal), agregados por producto y por personal, y el detalle completo
    cronológico. Es el único registro que queda de los movimientos de "Errores" una vez cerrado
    el turno."""
    wb = Workbook()
    _hoja_resumen(wb, turno, totales_tipo, admin_nombre)
    _hoja_fichajes(wb, fichajes or [])
    _hoja_stock(wb, stock)

    # "Errores" primero: es el único concepto que desaparece de la app tras el cierre.
    orden_tipos = ["errores"] + [t for t in db.TIPOS if t != "errores"]
    for t in orden_tipos:
        movimientos_tipo = [m for m in movimientos if m["tipo"] == t]
        _hoja_tipo(wb, t, movimientos_tipo)

    por_producto = _agrupar(movimientos, lambda m: m["producto_nombre"])
    _hoja_agrupada(wb, "Por producto", "Producto", por_producto)

    por_personal = _agrupar(movimientos, lambda m: m["empleada_nombre"] or "Sin asignar")
    _hoja_agrupada(wb, "Por personal", "Personal", por_personal)

    _hoja_todo(wb, movimientos)

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


def enviar_informe_turno(turno, movimientos, totales_tipo, admin_nombre, fichajes=None, stock=None):
    """Devuelve (ok, mensaje). No lanza excepción: si falla el envío, el cierre debe continuar igualmente."""
    ajustes = ajustes_smtp()
    if not ajustes["user"] or not ajustes["password"]:
        return False, "Envío de correo no configurado — ve a Configuración para añadir el remitente"
    if not ajustes["destino"]:
        return False, "No hay correo de destino configurado — ve a Configuración"

    destinatarios = [d.strip() for d in ajustes["destino"].split(",") if d.strip()]

    html = construir_informe_html(turno, movimientos, totales_tipo, admin_nombre, fichajes, stock)
    excel = construir_excel_informe(turno, movimientos, totales_tipo, admin_nombre, fichajes, stock)

    msg = MIMEMultipart()
    msg["Subject"] = f"Cierre de turno {turno['cerrado_en']}"
    msg["From"] = ajustes["user"]
    msg["To"] = ", ".join(destinatarios)
    msg.attach(MIMEText(html, "html", "utf-8"))

    adjunto = MIMEApplication(
        excel.read(),
        _subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    nombre_fichero = f"cierre_{turno['cerrado_en'].replace(':', '-')}.xlsx"
    adjunto.add_header("Content-Disposition", "attachment", filename=nombre_fichero)
    msg.attach(adjunto)

    return _enviar(msg, destinatarios, ajustes)


def enviar_nueva_password(nueva_password, admin_nombre):
    """Para el 'he olvidado la contraseña' del login. Devuelve (ok, mensaje)."""
    ajustes = ajustes_smtp()
    if not ajustes["user"] or not ajustes["password"]:
        return False, "el envío de correo no está configurado"
    if not ajustes["destino"]:
        return False, "no hay correo de destino configurado"

    destinatarios = [d.strip() for d in ajustes["destino"].split(",") if d.strip()]
    html = f"""
    <p>Hola {admin_nombre},</p>
    <p>Nos han pedido restablecer la contraseña de acceso a Gestión interna. La nueva contraseña es:</p>
    <p style="font-size:1.3em"><b>{nueva_password}</b></p>
    <p>Puedes cambiarla por otra que prefieras en cualquier momento desde Configuración, una vez
    dentro.</p>
    <p>Si no has sido tú, entra y cámbiala cuanto antes.</p>
    """
    msg = MIMEMultipart()
    msg["Subject"] = "Nueva contraseña — Gestión interna"
    msg["From"] = ajustes["user"]
    msg["To"] = ", ".join(destinatarios)
    msg.attach(MIMEText(html, "html", "utf-8"))

    return _enviar(msg, destinatarios, ajustes)


def _enviar(msg, destinatarios, ajustes):
    try:
        with smtplib.SMTP(ajustes["host"], ajustes["port"], timeout=15) as server:
            server.starttls()
            server.login(ajustes["user"], ajustes["password"])
            server.sendmail(ajustes["user"], destinatarios, msg.as_string())
        return True, "Correo enviado"
    except Exception as e:
        return False, f"No se ha podido enviar el correo: {e}"
