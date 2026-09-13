import io
import smtplib
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


def construir_informe_html(turno, movimientos, totales_tipo, admin_nombre):
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
    <table border="1" cellpadding="4" cellspacing="0">
      <tr><th>Fecha</th><th>Tipo</th><th>Producto</th><th>Cant.</th><th>Valor</th><th>Personal</th><th>Motivo</th></tr>
      {filas}
    </table>
    """


CABECERA_FILL = PatternFill(start_color="F3E9D8", end_color="F3E9D8", fill_type="solid")
CABECERA_FONT = Font(bold=True)
EUROS = '#,##0.00 "€"'


def _autoajustar(ws, anchos):
    for i, ancho in enumerate(anchos, start=1):
        ws.column_dimensions[get_column_letter(i)].width = ancho


def construir_excel_informe(turno, movimientos, totales_tipo, admin_nombre):
    """Devuelve un BytesIO con el .xlsx: una hoja de resumen por tipo y otra con el detalle línea a línea."""
    wb = Workbook()

    resumen = wb.active
    resumen.title = "Resumen"
    resumen["A1"] = "Cierre de turno"
    resumen["A1"].font = Font(bold=True, size=14)
    resumen["A2"] = "Cerrado por"
    resumen["B2"] = turno["cerrado_por"] or admin_nombre
    resumen["A3"] = "Abierto"
    resumen["B3"] = turno["abierto_en"]
    resumen["A4"] = "Cerrado"
    resumen["B4"] = turno["cerrado_en"]

    fila = 6
    resumen.cell(row=fila, column=1, value="Concepto").font = CABECERA_FONT
    resumen.cell(row=fila, column=2, value="Nº movimientos").font = CABECERA_FONT
    resumen.cell(row=fila, column=3, value="Valor total").font = CABECERA_FONT
    for col in (1, 2, 3):
        resumen.cell(row=fila, column=col).fill = CABECERA_FILL
    total_general = 0.0
    for t in db.TIPOS:
        fila += 1
        resumen.cell(row=fila, column=1, value=db.TIPO_LABELS.get(t, t))
        resumen.cell(row=fila, column=2, value=totales_tipo[t]["n"])
        celda_valor = resumen.cell(row=fila, column=3, value=totales_tipo[t]["total"])
        celda_valor.number_format = EUROS
        total_general += totales_tipo[t]["total"]
    fila += 1
    resumen.cell(row=fila, column=1, value="Total").font = Font(bold=True)
    celda_total = resumen.cell(row=fila, column=3, value=total_general)
    celda_total.font = Font(bold=True)
    celda_total.number_format = EUROS
    resumen.cell(row=fila, column=1).font = Font(bold=True)
    _autoajustar(resumen, [16, 16, 14])

    detalle = wb.create_sheet("Movimientos")
    cabeceras = ["Fecha", "Concepto", "Producto", "Cantidad", "Unidad de valor", "Valor unitario",
                 "Valor total", "Personal", "Turno", "Motivo"]
    for col, texto in enumerate(cabeceras, start=1):
        c = detalle.cell(row=1, column=col, value=texto)
        c.font = CABECERA_FONT
        c.fill = CABECERA_FILL
        c.alignment = Alignment(horizontal="left")
    detalle.freeze_panes = "A2"

    for fila_idx, m in enumerate(movimientos, start=2):
        detalle.cell(row=fila_idx, column=1, value=m["fecha"])
        detalle.cell(row=fila_idx, column=2, value=db.TIPO_LABELS.get(m["tipo"], m["tipo"]))
        detalle.cell(row=fila_idx, column=3, value=m["producto_nombre"])
        detalle.cell(row=fila_idx, column=4, value=m["cantidad"])
        detalle.cell(row=fila_idx, column=5, value="coste" if m["tipo"] != "errores" else "precio de venta")
        if m["valor_unitario"] is not None:
            c = detalle.cell(row=fila_idx, column=6, value=m["valor_unitario"])
            c.number_format = EUROS
        if m["valor_total"] is not None:
            c = detalle.cell(row=fila_idx, column=7, value=m["valor_total"])
            c.number_format = EUROS
        detalle.cell(row=fila_idx, column=8, value=m["empleada_nombre"] or "")
        detalle.cell(row=fila_idx, column=9, value=db.TURNO_LABELS.get(m["turno"], m["turno"] or ""))
        detalle.cell(row=fila_idx, column=10, value=m["motivo"] or "")

    _autoajustar(detalle, [12, 14, 30, 10, 15, 14, 14, 16, 10, 30])

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


def enviar_informe_turno(turno, movimientos, totales_tipo, admin_nombre):
    """Devuelve (ok, mensaje). No lanza excepción: si falla el envío, el cierre debe continuar igualmente."""
    ajustes = ajustes_smtp()
    if not ajustes["user"] or not ajustes["password"]:
        return False, "Envío de correo no configurado — ve a Configuración para añadir el remitente"
    if not ajustes["destino"]:
        return False, "No hay correo de destino configurado — ve a Configuración"

    destinatarios = [d.strip() for d in ajustes["destino"].split(",") if d.strip()]

    html = construir_informe_html(turno, movimientos, totales_tipo, admin_nombre)
    excel = construir_excel_informe(turno, movimientos, totales_tipo, admin_nombre)

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
