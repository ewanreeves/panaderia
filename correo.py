import smtplib
from email.mime.text import MIMEText

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
    <table border="1" cellpadding="4" cellspacing="0">
      <tr><th>Fecha</th><th>Tipo</th><th>Producto</th><th>Cant.</th><th>Valor</th><th>Empleada</th><th>Motivo</th></tr>
      {filas}
    </table>
    """


def enviar_informe_turno(turno, movimientos, totales_tipo, admin_nombre):
    """Devuelve (ok, mensaje). No lanza excepción: si falla el envío, el cierre debe continuar igualmente."""
    ajustes = ajustes_smtp()
    if not ajustes["user"] or not ajustes["password"]:
        return False, "Envío de correo no configurado — ve a Configuración para añadir el remitente"
    if not ajustes["destino"]:
        return False, "No hay correo de destino configurado — ve a Configuración"

    destinatarios = [d.strip() for d in ajustes["destino"].split(",") if d.strip()]

    html = construir_informe_html(turno, movimientos, totales_tipo, admin_nombre)
    msg = MIMEText(html, "html", "utf-8")
    msg["Subject"] = f"Cierre de turno {turno['cerrado_en']}"
    msg["From"] = ajustes["user"]
    msg["To"] = ", ".join(destinatarios)

    try:
        with smtplib.SMTP(ajustes["host"], ajustes["port"], timeout=15) as server:
            server.starttls()
            server.login(ajustes["user"], ajustes["password"])
            server.sendmail(ajustes["user"], destinatarios, msg.as_string())
        return True, "Correo enviado"
    except Exception as e:
        return False, f"No se ha podido enviar el correo: {e}"
