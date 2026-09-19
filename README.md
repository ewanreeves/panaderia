# Gestión interna (merma, reciclaje, autoconsumo, errores, fichajes)

App sencilla para llevar el control interno de merma, reciclaje, autoconsumo y errores de caja,
al margen del TPV, más el fichaje de entrada/salida del personal.

## Poner en marcha

En el PC de la clienta, doble clic en **`iniciar.bat`** — busca actualizaciones (si hay internet y
está configurado el repositorio, ver más abajo), instala dependencias si han cambiado, y abre la app
en el navegador. Es el único icono que necesita la clienta.

Para desarrollo (en tu PC):
```
venv\Scripts\python.exe app.py
```

Abre http://127.0.0.1:5000. Hay dos formas de entrar:

- **Caja**: un único botón compartido, sin contraseña, para cualquiera del personal. Solo puede
  registrar tickets y fichar entrada/salida — no puede entrar a Productos, Personal, Informes ni
  Configuración (si prueba la URL directamente, la app le redirige a Registrar). Como el login ya
  no identifica a la persona, el desplegable "Quién registra" de cada ticket es obligatorio: hay
  que elegir el nombre siempre, no se puede enviar el formulario sin seleccionarlo.
- **Administración (Cristina)**: acceso completo con contraseña — por defecto `Panaderia2026`
  (cámbiala desde la propia app en Configuración, o en `config.py`, junto con `ADMIN_NOMBRE` si el
  nombre cambia).

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
   quién lo registra (obligatorio: todo el personal dado de alta, más Cristina al final de la lista) y
   el turno (mañana/tarde), y se registra de una vez. El valor se calcula solo a partir del coste/precio
   del producto.
3. **Turno (apertura/cierre de caja)**: arriba del todo en Registrar. Es independiente de la hora — se
   puede cerrar y abrir caja las veces que haga falta en un día. Al **cerrar turno**:
   - se envía un correo (con un Excel adjunto con todos los movimientos, más una pestaña con las horas
     de entrada y salida del personal que ha estado fichado durante el turno) con el informe de todo lo
     registrado desde la apertura, al correo configurado en **Configuración**;
   - los movimientos de tipo **Errores** de ese turno se BORRAN por completo (no quedan en Informes,
     pero sí quedan en ese Excel — es el único registro que sobrevive de ellos);
   - el resto (merma, reciclaje, autoconsumo) queda guardado como siempre.
   Mientras el turno está cerrado no se pueden registrar tickets, hay que pulsar "Abrir turno" primero.
   El total de Errores acumulado en el turno actual se ve en la burbuja junto al estado del turno.
4. **Personal** (solo Cristina): da de alta aquí a las dependientas — nombre, apellidos, DNI y horas de
   jornada semanal. En cuanto exista una persona, aparece en el desplegable de Registrar y en el de
   Fichar.
5. **Fichar** (en Registrar, arriba de la carta): desplegable con todo el personal activo y dos
   botones, "Fichar entrada" y "Fichar salida". Se ve quién está fichada ahora mismo con la hora de
   entrada. Las horas que queden registradas son siempre las reales — la app no las redondea ni las
   ajusta a la jornada de contrato bajo ningún concepto, ni aunque se pasen de las horas pactadas: el
   registro horario tiene que reflejar la realidad, es obligatorio por ley (RD-ley 8/2019).
6. **Informes** (solo Cristina): totales por tipo, producto, personal y turno en un rango de fechas, con
   exportación a CSV para pasarlo a la gestoría si hace falta. Desde ahí, el botón "🕒 Horas de personal"
   lleva al detalle de fichajes de cada trabajadora en el rango elegido, con el total de horas por
   persona. Cristina puede **corregir** un fichaje (por ejemplo, si alguien no marcó un descanso o fue
   al médico y se le olvidó fichar) o **añadir uno a mano** si se le olvidó fichar del todo — en ambos
   casos hay que indicar el motivo de la corrección, que queda guardado junto con la fecha en que se
   hizo. Esto son correcciones de la realidad (algo que de verdad pasó y no se marcó bien), no un ajuste
   para que las horas cuadren con el contrato — eso seguiría sin reflejar lo que ha trabajado cada
   persona, que es justo lo que exige la ley.
7. **Configuración** (solo Cristina): correo de destino para los cierres de turno, cuenta de correo
   remitente (con contraseña de aplicación de Gmail), carpeta de copia de seguridad y cambio de su
   propia contraseña.

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

## Copia de seguridad en Drive

También desde **Configuración**. Cada cierre de turno guarda una copia de `data/app.db` (con marca de
fecha/hora, sin sobrescribir las anteriores) en la carpeta local que se indique. No se usa la API de
Google Drive (exigiría un proyecto en Google Cloud y volver a autenticar cada pocos días mientras la
app no esté verificada por Google) — en vez de eso, la carpeta debe ser una carpeta sincronizada por
**Google Drive para escritorio**, con la misma cuenta que envía los correos. La app solo deja el
fichero ahí; es Drive quien lo sube. Si no hay carpeta configurada o no existe, el cierre de turno
sigue funcionando igual, solo que sin copia de seguridad (se avisa por pantalla).

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
