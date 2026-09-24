# Gestión interna (merma, reciclaje, autoconsumo, errores, fichajes)

App sencilla para llevar el control interno de merma, reciclaje, autoconsumo y errores de caja,
al margen del TPV, más el fichaje de entrada/salida del personal.

## Poner en marcha

En el PC de la clienta, doble clic en **`iniciar.bat`**. Es el único icono que necesita la clienta.
La primera vez, si hace falta, instala solo Git y Python (con [winget](https://aka.ms/getwinget),
necesita internet), crea el entorno virtual e instala las dependencias; las siguientes veces solo
busca actualizaciones (`git pull`), comprueba dependencias y abre la app en el navegador. Si la
carpeta se copia a otro PC y el entorno virtual que trae no funciona ahí (pasa si Python estaba en
otra ruta en el PC original), `iniciar.bat` lo detecta solo y lo vuelve a crear — no hace falta
borrar nada a mano. Si algo falla de verdad (por ejemplo, no hay internet la primera vez y falta
Git o Python), se para con un mensaje claro en vez de fallar en silencio.

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
- **Administración (Cristina)**: acceso completo con contraseña — la de partida es la que tenga
  `APP_PASSWORD` en tu propio `config.py` (no se sube a git). Cámbiala cuanto antes desde la propia
  app en Configuración, o en `config.py`, junto con `ADMIN_NOMBRE` si el nombre cambia.

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
   quién lo registra (obligatorio) y el turno (mañana/tarde), y se registra de una vez. El valor se
   calcula solo a partir del coste/precio del producto. En el desplegable de "quién lo registra" solo
   aparece el personal que **ha fichado entrada** en ese momento (más Cristina, que no necesita fichar)
   — quien no ha fichado no puede registrar nada, ni saltándose el desplegable: la app lo comprueba
   también al guardar, no solo en la pantalla.
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
   jornada semanal. En cuanto exista una persona, aparece en el desplegable de Fichar (y en el de
   Registrar, una vez que fiche entrada — ver más abajo).
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
   remitente (con contraseña de aplicación de Gmail) y cambio de su propia contraseña. También explica
   la copia de seguridad automática (ver más abajo) y tiene un botón para **borrar los datos de
   demo** (movimientos, fichajes, turnos y personal — no toca productos ni esta configuración), pensado
   para dejar la app limpia justo antes de que la clienta empiece a usarla de verdad. Pide escribir
   "BORRAR" y confirmar aparte, y hace una copia de seguridad justo antes de borrar.

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

## Copia de seguridad

Automática, en local, sin configurar nada: cada cierre de turno guarda una copia de `data/app.db` en
la carpeta `backups/` (dentro de la propia carpeta de la app), con cuatro niveles de retención tipo
"abuelo-padre-hijo":

- **`backups/diario`**: la última copia de cada uno de los últimos 5 días.
- **`backups/semanal`**: una copia por semana, las últimas 4 semanas.
- **`backups/mensual`**: una copia por mes, los últimos 12 meses.
- **`backups/anual`**: una copia por año, los últimos 5 años.

Cada carpeta se poda por su cuenta, así que una copia ya promovida a semanal/mensual/anual no
desaparece cuando se poda el nivel diario. Si el cierre de turno hace dos copias el mismo día, en
`diario` solo se queda la más reciente de las dos.

Son copias solo en el propio PC (no se sube nada a ningún servicio en la nube — la clienta no tiene
cuenta de Google). Si se quiere una copia fuera del PC, hay que copiar la carpeta `backups/` a mano de
vez en cuando (a un USB, otro disco, etc.). Si por lo que sea falla la copia de seguridad, el cierre de
turno sigue funcionando igual (se avisa por pantalla).

## Actualizar la app en el PC de la clienta

El código vive en [github.com/ewanreeves/panaderia](https://github.com/ewanreeves/panaderia)
(repositorio **público** — el código en sí no es sensible; lo que sí lo es, `data/app.db` de la
clienta y `config.py` con sus contraseñas, está en `.gitignore` y nunca se sube). Al ser público, no
hace falta ninguna credencial para que `git pull` funcione solo en el PC de la clienta.

**En el PC de la clienta**, dos formas de llevar la app, las dos válidas:

- **`git clone`** (necesita Git ya instalado, o dejar que `iniciar.bat` lo instale solo la primera
  vez — ver más abajo): `git clone https://github.com/TU-USUARIO/NOMBRE-REPO.git`. Crea la carpeta
  ya conectada al repositorio, para que las actualizaciones futuras lleguen solas con `iniciar.bat`.
- **Copiar la carpeta entera** (USB, red, lo que sea) tal cual la tienes en tu PC, `venv/` incluido.
  No pasa nada si ese `venv/` no funciona en el PC de destino (es lo normal si Python estaba
  instalado en otra ruta) — `iniciar.bat` lo detecta y lo vuelve a crear solo. Si la carpeta ya
  incluye tu `data/app.db` y tu `config.py`, mejor: así no hay que reimportar productos ni volver a
  configurar el correo.

En cualquiera de los dos casos, el primer doble clic en `iniciar.bat` deja todo listo: instala Git
y Python si faltan (con winget, necesita internet), crea o repara el entorno virtual, instala las
dependencias, y si no existe `config.py` lo crea a partir de `config.example.py` (habría que
rellenarlo luego con la contraseña real y los datos de correo desde **Configuración**, dentro de la
propia app).

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
