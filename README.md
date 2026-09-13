# Gestión interna (merma, reciclaje, autoconsumo, errores)

App sencilla para llevar el control interno de merma, reciclaje, autoconsumo y errores de caja,
al margen del TPV.

## Poner en marcha

En el PC de la clienta, doble clic en **`iniciar.bat`** — busca actualizaciones (si hay internet y
está configurado el repositorio, ver más abajo), instala dependencias si han cambiado, y abre la app
en el navegador. Es el único icono que necesita la clienta.

Para desarrollo (en tu PC):
```
venv\Scripts\python.exe app.py
```

Abre http://127.0.0.1:5000. Hay dos formas de entrar:

- **Personal**: un botón por cada persona dada de alta (sin contraseña) — solo pueden registrar
  tickets, y en "Hoy" solo ven los suyos. No pueden entrar a Productos, Personal ni Informes
  (si prueban la URL directamente, la app les redirige a Registrar).
- **Administración (Cristina)**: acceso completo con contraseña — por defecto `Panaderia2026`
  (cámbiala en `config.py`, junto con `ADMIN_NOMBRE` si el nombre cambia).

Para cargar un catálogo y unos movimientos de ejemplo (útil para hacer una demo):

```
venv\Scripts\python.exe seed_demo.py
```

Esto borra `data/app.db` si existe y lo vuelve a crear con ~19 productos de panadería/cafetería
y unos días de movimientos de ejemplo. No lo ejecutes sobre datos reales de la clienta.

## Uso

1. **Productos**: añade productos a mano o impórtalos desde un Excel/CSV exportado del back office de GOTPV
   (en el paso de importación puedes indicar qué columna es el nombre, precio, coste, etc.).
2. **Registrar**: pantalla tipo TPV — se van tocando los productos de la carta (pueden ser varios, de
   categorías distintas) para montar un ticket, se elige el tipo (merma/reciclaje/autoconsumo/errores),
   quién lo registra y el turno (mañana/tarde), y se registra de una vez. El valor se calcula solo a
   partir del coste/precio del producto.
3. **Turno (apertura/cierre de caja)**: arriba del todo en Registrar. Es independiente de la hora — se
   puede cerrar y abrir caja las veces que haga falta en un día. Al **cerrar turno**:
   - se envía un correo (con un Excel adjunto con todos los movimientos) con el informe de todo lo
     registrado desde la apertura, al correo configurado en **Configuración**;
   - los movimientos de tipo **Errores** de ese turno se BORRAN por completo (no quedan en Informes);
   - el resto (merma, reciclaje, autoconsumo) queda guardado como siempre.
   Mientras el turno está cerrado no se pueden registrar tickets, hay que pulsar "Abrir turno" primero.
   El total de Errores acumulado en el turno actual se ve en la burbuja junto al estado del turno.
4. **Personal** (solo Cristina): da de alta aquí a las dependientas — en cuanto exista una, aparece como
   botón de acceso directo en la pantalla de login.
5. **Informes** (solo Cristina): totales por tipo, producto, personal y turno en un rango de fechas, con
   exportación a CSV para pasarlo a la gestoría si hace falta.
6. **Configuración** (solo Cristina): correo de destino para los cierres de turno, cuenta de correo
   remitente (con contraseña de aplicación de Gmail) y cambio de su propia contraseña.

## Correo al cerrar turno

Se configura desde la propia app: **Configuración** (solo Cristina) — ahí se pone a qué correo
llegan los cierres y la cuenta que los envía. No hace falta crear una cuenta nueva: puede ser el
Gmail personal o del negocio de Cristina, autenticado con una "contraseña de aplicación" (un código
de 16 letras que Google genera para que apps externas puedan enviar en su nombre, revocable en
cualquier momento, sin exponer la contraseña real de la cuenta). La propia pantalla de Configuración
trae el paso a paso para generarla.

Mientras no esté configurado, el cierre de turno funciona igual (se borran los errores, se cierra la
caja) pero no sale el correo — se avisa por pantalla.

`config.py` sigue teniendo `SMTP_HOST`/`SMTP_PORT`/`EMAIL_DESTINO`/`SMTP_USER`/`SMTP_PASSWORD` como
valores por defecto (útiles para variables de entorno en un despliegue), pero lo guardado desde
Configuración manda siempre sobre eso.

## Actualizar la app en el PC de la clienta

El proyecto ya es un repositorio git (`git init` hecho, primer commit hecho). `data/` (la base de datos
real de la clienta) y `config.py` (sus contraseñas) están en `.gitignore` — un `git pull` nunca los toca,
solo actualiza el código. Para dejarlo funcionando de verdad falta un paso único que tienes que hacer tú
con tu cuenta:

**Una vez, desde tu PC:**
1. Crea un repositorio **privado** en GitHub (github.com → New repository → Private).
2. Conéctalo y sube el código:
   ```
   git remote add origin https://github.com/TU-USUARIO/NOMBRE-REPO.git
   git branch -M main
   git push -u origin main
   ```

**Una vez, en el PC de la clienta** (necesita [Git for Windows](https://git-scm.com/download/win)
instalado — instalador normal, todo por defecto):
```
git clone https://github.com/TU-USUARIO/NOMBRE-REPO.git
```
Eso crea la carpeta del proyecto ya conectada al repositorio. Copia dentro tu `venv/` (o créalo de
nuevo con `py -m venv venv` + `venv\Scripts\python.exe -m pip install -r requirements.txt`), copia
`config.example.py` como `config.py` y rellénalo con la contraseña real y los datos de correo.

**A partir de ahí**, cada vez que quieras publicar un cambio: edítalo aquí, `git add -A`,
`git commit -m "..."`, `git push`. La próxima vez que la clienta (o quien sea) haga doble clic en
`iniciar.bat`, `git pull` se trae los cambios solo, sin que nadie tenga que hacer nada más. Si un día
no hay internet, `iniciar.bat` sigue arrancando igual con la versión que ya tenía.

## Datos

Todo se guarda en `data/app.db` (SQLite), en esta misma carpeta. Cópiala si quieres hacer una copia de
seguridad.

## Pendiente para producción

- Desplegar en un servidor propio o VPS con este proceso corriendo detrás de un proxy (o usar `waitress`/`gunicorn`).
- Cambiar `APP_PASSWORD` y `SECRET_KEY` en `config.py` (o por variables de entorno).
- Configurar HTTPS si se va a acceder desde fuera de la red local.
