import smtplib
from email.mime.text import MIMEText

import config
import database as db


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
    <table border="1" cellpadding="4" cellspacing="0">
      <tr><th>Fecha</th><th>Tipo</th><th>Producto</th><th>Cant.</th><th>Valor</th><th>Empleada</th><th>Motivo</th></tr>
      {filas}
    </table>
    """


def enviar_informe_turno(turno, movimientos, totales_tipo, admin_nombre):
    """Devuelve (ok, mensaje). No lanza excepción: si falla el envío, el cierre debe continuar igualmente."""
    if not config.SMTP_USER or not config.SMTP_PASSWORD:
        return False, "Envío de correo no configurado (faltan SMTP_USER/SMTP_PASSWORD en config.py)"

    html = construir_informe_html(turno, movimientos, totales_tipo, admin_nombre)
    msg = MIMEText(html, "html", "utf-8")
    msg["Subject"] = f"Cierre de turno {turno['cerrado_en']}"
    msg["From"] = config.SMTP_USER
    msg["To"] = config.EMAIL_DESTINO

    try:
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=15) as server:
            server.starttls()
            server.login(config.SMTP_USER, config.SMTP_PASSWORD)
            server.sendmail(config.SMTP_USER, [config.EMAIL_DESTINO], msg.as_string())
        return True, "Correo enviado"
    except Exception as e:
        return False, f"No se ha podido enviar el correo: {e}"
