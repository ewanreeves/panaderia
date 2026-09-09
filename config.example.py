"""Plantilla de configuración. Copia este fichero como config.py (que NO se sube a git —
cada instalación tiene el suyo con sus propios datos) y rellena los valores reales."""
import os

# Nombre y contraseña de la administradora (acceso completo: informes, productos, empleadas).
ADMIN_NOMBRE = os.environ.get("ADMIN_NOMBRE", "Cristina")
APP_PASSWORD = os.environ.get("APP_PASSWORD", "cambia-esta-contraseña")

# Clave usada para firmar la sesión de Flask. Cambiar en producción.
SECRET_KEY = os.environ.get("SECRET_KEY", "cambia-esta-clave-en-produccion")

# Envío del informe por correo al cerrar un turno.
# SMTP_USER/SMTP_PASSWORD deben ser los de la cuenta que ENVÍA el correo. Con Gmail hace falta una
# "contraseña de aplicación" (no la contraseña normal de la cuenta): myaccount.google.com/apppasswords
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
EMAIL_DESTINO = os.environ.get("EMAIL_DESTINO", "")
