import io
import csv
import json
import secrets
import hashlib
from datetime import date, datetime
from functools import wraps
from pathlib import Path

from flask import (
    Flask, render_template, request, redirect, url_for, session, flash, send_file, abort
)
from PIL import Image

import config
import database as db
import importador
import correo
import respaldo
import gotpv_import
from iconos import icono_para_producto

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = 400 * 1024 * 1024  # backups de GOTPV pueden pesar varios cientos de MB

UPLOAD_DIR = Path(__file__).parent / "data" / "tmp"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

db.init_db()


@app.context_processor
def inject_iconos():
    return {
        "tipo_icons": db.TIPO_ICONOS,
        "categoria_iconos": db.CATEGORIA_ICONOS,
        "categoria_icono_defecto": db.CATEGORIA_ICONO_DEFECTO,
        "turno_labels": db.TURNO_LABELS,
    }


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("rol"):
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("rol"):
            return redirect(url_for("login", next=request.path))
        if session.get("rol") != "admin":
            flash("Esa sección solo la puede usar la administración")
            return redirect(url_for("registro"))
        return view(*args, **kwargs)
    return wrapped


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        password = request.form.get("password", "")
        if password == db.get_config("admin_password", config.APP_PASSWORD):
            session.clear()
            session["rol"] = "admin"
            session["nombre"] = config.ADMIN_NOMBRE
            destino = request.args.get("next") or url_for("informes")
            return redirect(destino)
        flash("Contraseña incorrecta")
    return render_template("login.html", admin_nombre=config.ADMIN_NOMBRE)


@app.route("/login/recuperar", methods=["POST"])
def login_recuperar():
    ultimo = db.get_config("recuperacion_ultimo_envio")
    ahora = datetime.now()
    if ultimo:
        transcurrido = ahora - datetime.fromisoformat(ultimo)
        if transcurrido.total_seconds() < 300:
            flash("Ya se ha enviado una contraseña nueva hace un momento — revisa el correo.")
            return redirect(url_for("login"))

    destino = correo.ajustes_smtp()["destino"]
    if not destino:
        flash("No hay ningún correo configurado para recuperar la contraseña. Contacta con quien mantiene la app.")
        return redirect(url_for("login"))

    anterior = db.get_config("admin_password", config.APP_PASSWORD)
    nueva = secrets.token_urlsafe(6)
    db.set_config("admin_password", nueva)

    ok, mensaje = correo.enviar_nueva_password(nueva, config.ADMIN_NOMBRE)
    if ok:
        db.set_config("recuperacion_ultimo_envio", ahora.isoformat(timespec="seconds"))
        flash("Te hemos enviado una contraseña nueva por correo. La anterior ha dejado de funcionar.")
    else:
        db.set_config("admin_password", anterior)
        flash(f"No se ha podido enviar el correo ({mensaje}). La contraseña no se ha cambiado — inténtalo más tarde.")
    return redirect(url_for("login"))


@app.route("/login/caja", methods=["POST"])
def login_caja():
    session.clear()
    session["rol"] = "empleada"
    session["nombre"] = "Caja"
    return redirect(url_for("registro"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    if session.get("rol") == "admin":
        return redirect(url_for("informes"))
    return redirect(url_for("registro"))


# ---------- productos ----------

@app.route("/productos")
@admin_required
def productos():
    return render_template("productos.html", productos=db.list_productos())


@app.route("/productos/nuevo", methods=["POST"])
@admin_required
def productos_nuevo():
    nombre = request.form.get("nombre", "").strip()
    if not nombre:
        flash("El nombre es obligatorio")
        return redirect(url_for("productos"))
    db.insert_producto(
        nombre=nombre,
        categoria=request.form.get("categoria") or None,
        precio_venta=importador.parse_numero(request.form.get("precio_venta")),
        coste=importador.parse_numero(request.form.get("coste")),
        unidad=request.form.get("unidad") or "ud",
    )
    flash(f'Producto "{nombre}" añadido')
    return redirect(url_for("productos"))


@app.route("/productos/<int:producto_id>/editar", methods=["GET", "POST"])
@admin_required
def productos_editar(producto_id):
    producto = db.get_producto(producto_id)
    if not producto:
        abort(404)
    if request.method == "POST":
        db.update_producto(
            producto_id,
            nombre=request.form.get("nombre", "").strip(),
            categoria=request.form.get("categoria") or None,
            precio_venta=importador.parse_numero(request.form.get("precio_venta")),
            coste=importador.parse_numero(request.form.get("coste")),
            unidad=request.form.get("unidad") or "ud",
        )
        flash("Producto actualizado")
        return redirect(url_for("productos"))
    return render_template("productos_editar.html", p=producto)


@app.route("/productos/<int:producto_id>/eliminar", methods=["POST"])
@admin_required
def productos_eliminar(producto_id):
    if not db.get_producto(producto_id):
        abort(404)
    db.set_producto_activo(producto_id, activo=False)
    flash("Producto archivado")
    return redirect(url_for("productos"))


@app.route("/productos/importar", methods=["GET", "POST"])
@admin_required
def productos_importar():
    if request.method == "POST":
        fichero = request.files.get("fichero")
        if not fichero or not fichero.filename:
            flash("Selecciona un fichero CSV o Excel")
            return redirect(url_for("productos_importar"))
        destino = UPLOAD_DIR / f"import{Path(fichero.filename).suffix.lower()}"
        fichero.save(destino)
        try:
            tabla = importador.leer_fichero(destino)
        except Exception as e:
            flash(f"No se ha podido leer el fichero: {e}")
            return redirect(url_for("productos_importar"))
        columnas = list(tabla.columns)
        mapeo_sugerido = importador.sugerir_mapeo(columnas)
        preview = tabla.head(5).to_dict(orient="records")
        return render_template(
            "productos_importar_mapeo.html",
            columnas=columnas,
            mapeo=mapeo_sugerido,
            preview=preview,
            campos=importador.CAMPOS_DESTINO,
            nombre_fichero=destino.name,
            total_filas=len(tabla),
        )
    return render_template("productos_importar.html")


@app.route("/productos/importar/confirmar", methods=["POST"])
@admin_required
def productos_importar_confirmar():
    nombre_fichero = request.form.get("nombre_fichero")
    origen = UPLOAD_DIR / nombre_fichero if nombre_fichero else None
    if not origen or not origen.exists():
        flash("El fichero ha expirado, vuelve a subirlo")
        return redirect(url_for("productos_importar"))

    tabla = importador.leer_fichero(origen)
    col_nombre = request.form.get("map_nombre")
    col_categoria = request.form.get("map_categoria")
    col_precio = request.form.get("map_precio_venta")
    col_coste = request.form.get("map_coste")
    col_unidad = request.form.get("map_unidad")

    if not col_nombre or col_nombre not in tabla.columns:
        flash("Tienes que indicar qué columna es el nombre del producto")
        return redirect(url_for("productos_importar"))

    nuevos, actualizados, omitidos = 0, 0, 0
    for _, fila in tabla.iterrows():
        nombre = str(fila.get(col_nombre, "")).strip()
        if not nombre:
            omitidos += 1
            continue
        _, creado = db.upsert_producto_from_import(
            nombre=nombre,
            categoria=str(fila.get(col_categoria, "")).strip() or None if col_categoria else None,
            precio_venta=importador.parse_numero(fila.get(col_precio)) if col_precio else None,
            coste=importador.parse_numero(fila.get(col_coste)) if col_coste else None,
            unidad=str(fila.get(col_unidad, "")).strip() or None if col_unidad else None,
        )
        if creado:
            nuevos += 1
        else:
            actualizados += 1

    origen.unlink(missing_ok=True)
    flash(f"Importación completa: {nuevos} productos nuevos, {actualizados} actualizados, {omitidos} filas omitidas")
    return redirect(url_for("productos"))


@app.route("/productos/importar-gotpv", methods=["GET", "POST"])
@admin_required
def productos_importar_gotpv():
    if request.method == "POST":
        fichero = request.files.get("fichero")
        if not fichero or not fichero.filename:
            flash("Selecciona el fichero de backup (.sql) de GOTPV")
            return redirect(url_for("productos_importar_gotpv"))

        destino = UPLOAD_DIR / "gotpv_backup.sql"
        fichero.save(destino)
        try:
            data = destino.read_bytes()
            productos = gotpv_import.extraer_productos(data)
        except gotpv_import.ErrorImportacionGOTPV as e:
            flash(f"No se ha podido leer el backup: {e}")
            return redirect(url_for("productos_importar_gotpv"))
        finally:
            destino.unlink(missing_ok=True)

        if not productos:
            flash("No se ha encontrado ningún artículo en ese backup")
            return redirect(url_for("productos_importar_gotpv"))

        fotos_dir = Path(__file__).parent / "static" / "productos_fotos"
        fotos_dir.mkdir(parents=True, exist_ok=True)

        nuevos, actualizados, fotos_nuevas = 0, 0, 0
        for p in productos:
            foto_nombre = None
            if p["imagen"]:
                h = hashlib.sha1(p["imagen"]).hexdigest()[:16]
                foto_nombre = f"{h}.png"
                ruta_foto = fotos_dir / foto_nombre
                if not ruta_foto.exists():
                    try:
                        with Image.open(io.BytesIO(p["imagen"])) as im:
                            im.convert("RGB").save(ruta_foto, "PNG", optimize=True)
                        fotos_nuevas += 1
                    except Exception:
                        foto_nombre = None

            _, creado = db.upsert_producto_from_import(
                nombre=p["nombre"],
                categoria=p["categoria"],
                precio_venta=p["pvp"],
                coste=p["coste"],
                unidad=p["medida"],
                foto=foto_nombre,
            )
            if creado:
                nuevos += 1
            else:
                actualizados += 1

        flash(
            f"Backup de GOTPV importado: {nuevos} productos nuevos, {actualizados} actualizados, "
            f"{fotos_nuevas} fotos nuevas"
        )
        return redirect(url_for("productos"))

    return render_template("productos_importar_gotpv.html")


# ---------- personal ----------

@app.route("/personal")
@admin_required
def personal():
    return render_template("personal.html", empleadas=db.list_empleadas())


@app.route("/personal/nuevo", methods=["POST"])
@admin_required
def personal_nuevo():
    nombre = request.form.get("nombre", "").strip()
    if not nombre:
        flash("El nombre es obligatorio")
        return redirect(url_for("personal"))
    db.insert_empleada(
        nombre,
        apellidos=request.form.get("apellidos", "").strip() or None,
        dni=request.form.get("dni", "").strip() or None,
        horas_semanales=importador.parse_numero(request.form.get("horas_semanales")),
    )
    flash(f'"{nombre}" añadido al personal')
    return redirect(url_for("personal"))


@app.route("/personal/<int:empleada_id>/editar", methods=["GET", "POST"])
@admin_required
def personal_editar(empleada_id):
    empleada = db.get_empleada(empleada_id)
    if not empleada:
        abort(404)
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        if not nombre:
            flash("El nombre es obligatorio")
            return redirect(url_for("personal_editar", empleada_id=empleada_id))
        db.update_empleada(
            empleada_id,
            nombre,
            apellidos=request.form.get("apellidos", "").strip() or None,
            dni=request.form.get("dni", "").strip() or None,
            horas_semanales=importador.parse_numero(request.form.get("horas_semanales")),
        )
        flash("Actualizado")
        return redirect(url_for("personal"))
    return render_template("personal_editar.html", e=empleada)


@app.route("/personal/<int:empleada_id>/eliminar", methods=["POST"])
@admin_required
def personal_eliminar(empleada_id):
    if not db.get_empleada(empleada_id):
        abort(404)
    db.set_empleada_activa(empleada_id, activo=False)
    flash("Archivado")
    return redirect(url_for("personal"))


# ---------- registro de movimientos ----------

@app.route("/registro", methods=["GET", "POST"])
@login_required
def registro():
    rol = session.get("rol")

    if request.method == "POST":
        if not db.get_turno_abierto():
            flash("El turno está cerrado — ábrelo antes de registrar")
            return redirect(url_for("registro"))

        tipo = request.form.get("tipo")
        fecha = request.form.get("fecha") or date.today().isoformat()
        motivo = request.form.get("motivo") or None
        turno = request.form.get("turno") or None

        if tipo not in db.TIPOS:
            flash("Selecciona el tipo de movimiento")
            return redirect(url_for("registro"))

        seleccion = request.form.get("empleada_id")
        if not seleccion:
            flash("Selecciona quién registra el ticket")
            return redirect(url_for("registro"))
        if seleccion == "admin":
            empleada_id_db = None
            empleada_nombre = config.ADMIN_NOMBRE
        else:
            empleada = db.get_empleada(seleccion)
            if not empleada:
                flash("Selecciona quién registra el ticket")
                return redirect(url_for("registro"))
            empleada_id_db = empleada["id"]
            empleada_nombre = empleada["nombre"]

        try:
            lineas = json.loads(request.form.get("lineas") or "[]")
        except ValueError:
            lineas = []
        if not lineas:
            flash("Añade al menos un producto al ticket")
            return redirect(url_for("registro"))

        lote = secrets.token_hex(4)
        registrados = 0
        for linea in lineas:
            try:
                producto = db.get_producto(int(linea.get("producto_id")))
                cantidad = float(linea.get("cantidad"))
            except (TypeError, ValueError):
                continue
            if not producto or cantidad <= 0:
                continue
            if tipo == "errores":
                valor_unitario = producto["precio_venta"]
            else:
                valor_unitario = producto["coste"] if producto["coste"] is not None else producto["precio_venta"]
            db.insert_movimiento(
                producto_id=producto["id"],
                producto_nombre=producto["nombre"],
                tipo=tipo,
                cantidad=cantidad,
                valor_unitario=valor_unitario,
                motivo=motivo,
                fecha=fecha,
                lote=lote,
                empleada_id=empleada_id_db,
                empleada_nombre=empleada_nombre,
                turno=turno,
            )
            registrados += 1

        if registrados:
            plural = "producto" if registrados == 1 else "productos"
            flash(f"Ticket registrado: {registrados} {plural} — {db.TIPO_LABELS[tipo]}")
        else:
            flash("No se ha podido registrar ningún producto del ticket")
        return redirect(url_for("registro"))

    productos = db.list_productos()
    categorias = []
    por_categoria = {}
    for p in productos:
        cat = p["categoria"] or "Otros"
        if cat not in por_categoria:
            por_categoria[cat] = []
            categorias.append(cat)
        por_categoria[cat].append({
            "id": p["id"],
            "nombre": p["nombre"],
            "precio_venta": p["precio_venta"],
            "foto": p["foto"],
            "icono": icono_para_producto(p["nombre"], cat, db.CATEGORIA_ICONOS, db.CATEGORIA_ICONO_DEFECTO),
        })
    hoy = date.today().isoformat()
    de_hoy = [m for m in db.list_movimientos() if m["fecha"] == hoy]
    total_hoy = sum(m["valor_total"] or 0 for m in de_hoy)

    tickets_hoy = []
    por_clave = {}
    orden_claves = []
    for m in de_hoy:
        clave = m["lote"] or f"m{m['id']}"
        if clave not in por_clave:
            por_clave[clave] = []
            orden_claves.append(clave)
        por_clave[clave].append(m)
    for clave in orden_claves:
        lineas_ticket = por_clave[clave]
        tickets_hoy.append({
            "lote": lineas_ticket[0]["lote"],
            "movimiento_id": lineas_ticket[0]["id"],
            "tipo": lineas_ticket[0]["tipo"],
            "motivo": lineas_ticket[0]["motivo"],
            "empleada_nombre": lineas_ticket[0]["empleada_nombre"],
            "turno": lineas_ticket[0]["turno"],
            "lineas": lineas_ticket,
            "total": sum(l["valor_total"] or 0 for l in lineas_ticket),
        })

    turno_abierto = db.get_turno_abierto()
    total_errores_turno = 0
    if turno_abierto:
        total_errores_turno, _ = db.total_errores_desde(turno_abierto["abierto_en"])

    empleadas = db.list_empleadas()
    ids_fichadas = {f["empleada_id"] for f in db.fichajes_activos()}

    return render_template(
        "registro.html",
        categorias=categorias,
        por_categoria=por_categoria,
        tipos=db.TIPOS,
        tipo_labels=db.TIPO_LABELS,
        empleadas=empleadas,
        turnos=db.TURNOS,
        turno_abierto=turno_abierto,
        total_errores_turno=total_errores_turno,
        hoy=hoy,
        tickets_hoy=tickets_hoy,
        total_hoy=total_hoy,
        rol=rol,
        admin_nombre=config.ADMIN_NOMBRE,
        fichajes_activos=db.fichajes_activos(),
        ids_fichadas=ids_fichadas,
    )


@app.route("/registro/<int:movimiento_id>/eliminar", methods=["POST"])
@login_required
def registro_eliminar(movimiento_id):
    db.delete_movimiento(movimiento_id)
    flash("Movimiento eliminado")
    return redirect(request.referrer or url_for("registro"))


@app.route("/registro/lote/<lote>/eliminar", methods=["POST"])
@login_required
def registro_lote_eliminar(lote):
    db.delete_movimientos_por_lote(lote)
    flash("Ticket eliminado")
    return redirect(request.referrer or url_for("registro"))


# ---------- fichajes ----------

@app.route("/fichar", methods=["POST"])
@login_required
def fichar():
    empleada_id = request.form.get("empleada_id")
    accion = request.form.get("accion")
    empleada = db.get_empleada(empleada_id) if empleada_id else None
    if not empleada:
        flash("Selecciona quién ficha")
        return redirect(url_for("registro"))

    abierto = db.get_fichaje_abierto(empleada["id"])
    if accion == "entrada":
        if abierto:
            flash(f'{empleada["nombre"]} ya tiene fichada la entrada de las {abierto["entrada"][11:16]}')
        else:
            db.fichar_entrada(empleada["id"], empleada["nombre"])
            flash(f'Entrada fichada: {empleada["nombre"]}')
    elif accion == "salida":
        if not abierto:
            flash(f'{empleada["nombre"]} no tiene ninguna entrada fichada')
        else:
            db.fichar_salida(abierto["id"])
            flash(f'Salida fichada: {empleada["nombre"]}')
    else:
        flash("Acción no válida")
    return redirect(url_for("registro"))


# ---------- apertura / cierre de turno ----------

@app.route("/turno/abrir", methods=["POST"])
@login_required
def turno_abrir():
    if db.get_turno_abierto():
        flash("Ya hay un turno abierto")
        return redirect(url_for("registro"))
    db.abrir_turno(session.get("nombre"))
    flash("Turno abierto")
    return redirect(url_for("registro"))


@app.route("/turno/cerrar", methods=["POST"])
@login_required
def turno_cerrar():
    turno = db.get_turno_abierto()
    if not turno:
        flash("No hay ningún turno abierto")
        return redirect(url_for("registro"))

    ahora = datetime.now().isoformat(timespec="seconds")
    movimientos = db.movimientos_del_turno(turno["abierto_en"], ahora)
    fichajes = db.fichajes_del_turno(turno["abierto_en"], ahora)
    totales_tipo = {
        t: {
            "n": sum(1 for m in movimientos if m["tipo"] == t),
            "total": sum(m["valor_total"] or 0 for m in movimientos if m["tipo"] == t),
        }
        for t in db.TIPOS
    }
    turno_para_correo = dict(turno)
    turno_para_correo["cerrado_en"] = ahora
    turno_para_correo["cerrado_por"] = session.get("nombre")

    ok, mensaje = correo.enviar_informe_turno(
        turno_para_correo, movimientos, totales_tipo, config.ADMIN_NOMBRE, fichajes
    )

    db.eliminar_errores_desde(turno["abierto_en"], ahora)
    db.cerrar_turno(turno["id"], session.get("nombre"), email_enviado=ok)

    ok_backup, mensaje_backup = respaldo.hacer_backup()

    partes = ["Turno cerrado."]
    partes.append("Informe enviado por correo." if ok else f"Correo no enviado ({mensaje.lower()}).")
    partes.append("Copia de seguridad guardada." if ok_backup else f"Sin copia de seguridad ({mensaje_backup}).")
    partes.append("Los errores del turno se han borrado.")
    flash(" ".join(partes))
    return redirect(url_for("registro"))


# ---------- informes ----------

@app.route("/informes")
@admin_required
def informes():
    fecha_desde = request.args.get("desde") or date.today().replace(day=1).isoformat()
    fecha_hasta = request.args.get("hasta") or date.today().isoformat()
    tipo = request.args.get("tipo") or None
    empleada_id = request.args.get("empleada") or None

    movimientos = db.list_movimientos(fecha_desde, fecha_hasta, tipo, empleada_id)
    totales_tipo = db.totales_por_tipo(fecha_desde, fecha_hasta)
    por_producto = db.totales_por_producto(fecha_desde, fecha_hasta, tipo)
    por_empleada = db.totales_por_empleada(fecha_desde, fecha_hasta, tipo)
    por_turno = db.totales_por_turno(fecha_desde, fecha_hasta, tipo)
    total_general = sum(t["total"] for t in totales_tipo.values())

    return render_template(
        "informes.html",
        movimientos=movimientos,
        totales_tipo=totales_tipo,
        por_producto=por_producto,
        por_empleada=por_empleada,
        por_turno=por_turno,
        total_general=total_general,
        tipo_labels=db.TIPO_LABELS,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        tipo_actual=tipo,
        empleada_actual=empleada_id,
        empleadas=db.list_empleadas(),
    )


@app.route("/informes/exportar.csv")
@admin_required
def informes_exportar():
    fecha_desde = request.args.get("desde") or date.today().replace(day=1).isoformat()
    fecha_hasta = request.args.get("hasta") or date.today().isoformat()
    tipo = request.args.get("tipo") or None
    empleada_id = request.args.get("empleada") or None
    movimientos = db.list_movimientos(fecha_desde, fecha_hasta, tipo, empleada_id)

    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow(["Fecha", "Tipo", "Producto", "Cantidad", "Valor unitario", "Valor total", "Personal", "Turno", "Motivo"])
    for m in movimientos:
        writer.writerow([
            m["fecha"], db.TIPO_LABELS.get(m["tipo"], m["tipo"]), m["producto_nombre"],
            m["cantidad"], m["valor_unitario"], m["valor_total"],
            m["empleada_nombre"] or "", db.TURNO_LABELS.get(m["turno"], m["turno"] or ""), m["motivo"] or "",
        ])
    mem = io.BytesIO(buffer.getvalue().encode("utf-8-sig"))
    return send_file(
        mem, mimetype="text/csv", as_attachment=True,
        download_name=f"informe_{fecha_desde}_a_{fecha_hasta}.csv",
    )


# ---------- horas de personal (consulta + correcciones) ----------

def _fichaje_a_datetime_local(valor):
    """'2026-09-19T08:03:00' -> '2026-09-19T08:03' (lo que espera un <input type=datetime-local>)."""
    return valor[:16] if valor else ""


def _datetime_local_a_iso(valor):
    """'2026-09-19T08:03' (del formulario) -> '2026-09-19T08:03:00' (lo que guarda la app)."""
    if not valor:
        return None
    return valor if len(valor) > 16 else valor + ":00"


@app.route("/informes/horas")
@admin_required
def informes_horas():
    fecha_desde = request.args.get("desde") or date.today().replace(day=1).isoformat()
    fecha_hasta = request.args.get("hasta") or date.today().isoformat()
    empleada_id = request.args.get("empleada") or None

    fichajes = db.fichajes_rango(f"{fecha_desde}T00:00:00", f"{fecha_hasta}T23:59:59", empleada_id)

    por_empleada = {}
    total_general = 0.0
    filas = []
    for f in fichajes:
        horas, en_curso = correo.horas_entre(f["entrada"], f["salida"])
        filas.append({"f": f, "horas": horas, "en_curso": en_curso})
        total_general += horas
        acumulado = por_empleada.setdefault(f["empleada_nombre"], 0.0)
        por_empleada[f["empleada_nombre"]] = acumulado + horas

    return render_template(
        "horas.html",
        filas=filas,
        por_empleada=sorted(por_empleada.items()),
        total_general=total_general,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        empleada_actual=empleada_id,
        empleadas=db.list_empleadas(),
    )


@app.route("/fichajes/nuevo", methods=["POST"])
@admin_required
def fichaje_nuevo():
    empleada = db.get_empleada(request.form.get("empleada_id"))
    entrada = _datetime_local_a_iso(request.form.get("entrada"))
    salida = _datetime_local_a_iso(request.form.get("salida"))
    motivo = request.form.get("motivo", "").strip()

    if not empleada or not entrada or not motivo:
        flash("Faltan datos: personal, hora de entrada y motivo de la corrección son obligatorios")
        return redirect(url_for("informes_horas"))
    if salida and salida < entrada:
        flash("La salida no puede ser antes que la entrada")
        return redirect(url_for("informes_horas"))

    db.insert_fichaje_manual(empleada["id"], empleada["nombre"], entrada, salida, motivo)
    flash(f'Fichaje añadido a mano para {empleada["nombre"]}')
    return redirect(url_for("informes_horas"))


@app.route("/fichajes/<int:fichaje_id>/editar", methods=["GET", "POST"])
@admin_required
def fichaje_editar(fichaje_id):
    fichaje = db.get_fichaje(fichaje_id)
    if not fichaje:
        abort(404)
    if request.method == "POST":
        entrada = _datetime_local_a_iso(request.form.get("entrada"))
        salida = _datetime_local_a_iso(request.form.get("salida"))
        motivo = request.form.get("motivo", "").strip()
        if not entrada or not motivo:
            flash("La hora de entrada y el motivo de la corrección son obligatorios")
            return redirect(url_for("fichaje_editar", fichaje_id=fichaje_id))
        if salida and salida < entrada:
            flash("La salida no puede ser antes que la entrada")
            return redirect(url_for("fichaje_editar", fichaje_id=fichaje_id))
        db.update_fichaje(fichaje_id, entrada, salida, motivo)
        flash(f'Fichaje de {fichaje["empleada_nombre"]} corregido')
        return redirect(url_for("informes_horas"))
    return render_template("fichaje_editar.html", f=fichaje)


@app.route("/fichajes/<int:fichaje_id>/eliminar", methods=["POST"])
@admin_required
def fichaje_eliminar(fichaje_id):
    fichaje = db.get_fichaje(fichaje_id)
    if not fichaje:
        abort(404)
    db.delete_fichaje(fichaje_id)
    flash(f'Fichaje de {fichaje["empleada_nombre"]} eliminado')
    return redirect(url_for("informes_horas"))


# ---------- configuración ----------

@app.route("/configuracion", methods=["GET", "POST"])
@admin_required
def configuracion():
    if request.method == "POST":
        email_destino = request.form.get("email_destino", "").strip()
        smtp_user = request.form.get("smtp_user", "").strip()
        smtp_password = request.form.get("smtp_password", "")

        db.set_config("email_destino", email_destino)
        db.set_config("smtp_user", smtp_user)
        if smtp_password:
            db.set_config("smtp_password", smtp_password)

        flash("Configuración guardada")
        return redirect(url_for("configuracion"))

    ajustes = correo.ajustes_smtp()
    return render_template(
        "configuracion.html",
        email_destino=ajustes["destino"] or "",
        smtp_user=ajustes["user"] or "",
        smtp_password_configurada=bool(ajustes["password"]),
    )


@app.route("/configuracion/password", methods=["POST"])
@admin_required
def configuracion_password():
    actual = request.form.get("actual", "")
    nueva = request.form.get("nueva", "")
    repetir = request.form.get("repetir", "")

    if actual != db.get_config("admin_password", config.APP_PASSWORD):
        flash("La contraseña actual no es correcta")
    elif not nueva or len(nueva) < 4:
        flash("La contraseña nueva tiene que tener al menos 4 caracteres")
    elif nueva != repetir:
        flash("La contraseña nueva no coincide en los dos campos")
    else:
        db.set_config("admin_password", nueva)
        flash("Contraseña actualizada")
    return redirect(url_for("configuracion"))


@app.route("/configuracion/borrar-demo", methods=["POST"])
@admin_required
def configuracion_borrar_demo():
    if request.form.get("confirmacion", "").strip().upper() != "BORRAR":
        flash('Para borrar los datos de demo hay que escribir "BORRAR" exactamente')
        return redirect(url_for("configuracion"))

    respaldo.hacer_backup()
    db.borrar_datos_demo()
    flash(
        "Datos de demo borrados: movimientos, fichajes, turnos y personal. "
        "Productos y configuración no se han tocado. Se hizo una copia de seguridad justo antes."
    )
    return redirect(url_for("configuracion"))


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
