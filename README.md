# Mesa de soporte

Aplicación Flask modular para Mesa de soporte. Incluye autenticación, administración de usuarios, el módulo Falla comunicación y el módulo Análisis de informes diarios. En desarrollo usa SQLite; para multiusuario se recomienda PostgreSQL.

## Estructura

```text
app/ __init__.py auth.py cli.py dashboard.py daily_reports.py falla_comunicacion.py models.py
static/css/app.css dashboard.css daily_reports.css
static/js/modules/ daily_reports.js falla_comunicacion.js
templates/ base.html login.html dashboard.html users.html modules/
config.py  run.py  requirements.txt
```

## Desarrollo local (Windows PowerShell)

Requiere Python 3.11 o posterior.

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
$env:SECRET_KEY = [Convert]::ToBase64String((1..48 | ForEach-Object { Get-Random -Maximum 256 }))
flask --app run.py init-db
flask --app run.py create-admin
flask --app run.py run
```

Abre `http://127.0.0.1:5000`. `create-admin` solicita las credenciales iniciales; la contraseña debe tener al menos 12 caracteres. No hay credenciales predeterminadas. Como admin puedes crear usuarios desde **Usuarios**.

### Informe de fallas en envíos programados

El informe programado de Falla comunicación utiliza el mismo generador de documento que la vista del módulo. Se genera nuevamente en cada ejecución con la última carga del periodo configurado; PDF, JPG y PNG incluyen el dashboard completo y Excel contiene los registros filtrados. La opción **Último informe cargado** resuelve el periodo más reciente al ejecutar el envío. El icono de documento en la programación abre una vista previa PDF sin enviar correos.

La generación automática usa Playwright y Microsoft Edge instalado en Windows, sin abrir ventanas visibles. En Linux instala el navegador con `python -m playwright install --with-deps chromium`. La variable `REPORT_BROWSER_CHANNEL` permite elegir `msedge`, `chrome` o `chromium` según el navegador instalado.

## PostgreSQL

Instala PostgreSQL 15+ y crea la base de datos y un usuario dedicado:

```sql
CREATE ROLE mesa_user LOGIN PASSWORD 'clave-larga-unica';
CREATE DATABASE mesa_soporte OWNER mesa_user;
```

Define el driver psycopg URL y secreto en el entorno antes de inicializar:

```powershell
$env:DATABASE_URL = 'postgresql+psycopg://mesa_user:clave-larga-unica@localhost:5432/mesa_soporte'
$env:SECRET_KEY = 'secreto-aleatorio-de-al-menos-32-bytes'
$env:COOKIE_SECURE = 'true'
flask --app run.py init-db
flask --app run.py create-admin
flask --app run.py run
```

Para HTTP local deja `COOKIE_SECURE=false`; en producción actívalo y sirve la aplicación detrás de un proxy inverso TLS que redirija HTTP a HTTPS. Usa el gestor de secretos del despliegue. `.env.example` es una plantilla; la aplicación carga el archivo local `.env`. Ejecuta producción detrás de un WSGI como `gunicorn -w 3 'run:app'`; configura respaldos, monitoreo y migraciones. `init-db` crea tablas faltantes y aplica las migraciones compatibles incluidas; usa Flask-Migrate/Alembic para cambios de esquema adicionales.

## Seguridad y roles

- **Admin:** crear y consultar usuarios.
- **Supervisor y agente:** pueden autenticarse; el menú se ampliará según los módulos futuros.

El formulario de administración registra nombres, apellidos, cédula, teléfonos, cargo, fechas de ingreso y nacimiento, correo y contacto de emergencia. Los administradores pueden editar perfiles, activar o desactivar cuentas, eliminar cuentas (anonimizando los datos y conservando referencias históricas) y enviar una contraseña temporal. Esta contraseña vence en 24 horas y obliga a definir una nueva al iniciar sesión. Cada usuario también puede cambiar su propia contraseña desde el enlace de la barra superior. `flask --app run.py init-db` agrega estos campos de forma compatible a la tabla existente; cédula y correo quedan protegidos con índices únicos.

### Correo para contraseñas temporales

Configura el servidor SMTP antes de usar **Enviar contraseña**. Para mantener la configuración entre reinicios, crea un archivo local `.env` (está excluido de Git) y completa los valores con los datos de tu proveedor:

```powershell
Copy-Item .env.example .env
notepad .env
```

Se requieren `MAIL_SERVER` y `MAIL_DEFAULT_SENDER`. Si el proveedor requiere autenticación, completa también `MAIL_USERNAME` y `MAIL_PASSWORD`; usa una contraseña de aplicación cuando aplique. `MAIL_PORT`, `MAIL_USE_TLS` y `MAIL_USE_SSL` deben coincidir con el proveedor. No dejes valores de ejemplo ni compartas el archivo `.env`. La aplicación lo carga al iniciar; después de guardarlo, reinicia Flask.

El acceso requiere login. Cinco intentos fallidos bloquean la cuenta 15 minutos; eventos quedan en `AuditLog`. ORM parametrizado, escape automático de Jinja, CSRF en formularios POST y cabeceras CSP, anti framing y `nosniff`. Las cookies son `HttpOnly` y `SameSite=Lax`; `Secure` se activa con `COOKIE_SECURE=true`. Para despliegue público añade limitación de tasa, gestión de claves, recuperación de cuenta y retención de auditoría según política organizacional.

El módulo de tickets y sus pantallas de importación/exportación se retiraron. Las tablas que pudieran existir de una instalación anterior no se borran automáticamente; el código actual ya no las expone. Continúa indicando qué módulo quieres agregar y definiremos sus pantallas y permisos antes de implementarlo.

## Módulo Falla comunicación

Disponible para usuarios autenticados. Admin y supervisor pueden cargar Excel `.xlsx`/`.xls` o CSV (hasta 10 MB y 10.000 filas); los registros se guardan en `failure_communication_case` y se sincronizan por ID de caso, mientras que cada carga queda auditada. Agentes tienen acceso de consulta. La columna `ESTADO` es obligatoria; las otras columnas se detectan por encabezados como ID, código, fecha de creación/actualización, zona, técnico, asunto, prioridad, tipo de solicitud, grupo, canal y creador. El tablero conserva los análisis y reportes del HTML fuente, y restaura los registros guardados al abrir el módulo.

## Módulo Análisis de informes diarios

Disponible para usuarios autenticados. Admin y supervisor pueden cargar una sábana `.xlsx` (hasta 10 MB y 50.000 registros por hoja) con validación y vista previa antes de confirmar. Antes de guardar, el usuario elige si conserva una copia histórica completa de las filas válidas. `Data` alimenta los KPIs generales con sincronización por ID; las otras hojas se guardan separadas porque pueden ser subconjuntos del mismo histórico. Las copias históricas se guardan en `daily_report_history_row` y pueden descargarse como Excel. El ID de solicitud es único en `daily_support_request` y las actualizaciones se aplican solo cuando la fecha de última actualización es más reciente. Los conflictos bloquean la confirmación. Cada carga queda auditada en `daily_report_import`.

En Informes diarios se selecciona el mes y año de los datos al validar cada carga; ese periodo se muestra en el resumen de la última sábana y en el historial de importaciones. Falla comunicación ofrece la misma selección y decisión explícita de guardar histórico; las copias se conservan en `failure_communication_history_row`, se pueden descargar en Excel y un administrador puede depurarlas sin borrar los casos operativos actuales. Ejecuta `flask --app run init-db` después de actualizar para crear las tablas y columnas requeridas.

El módulo **Indicadores** guarda los objetivos y porcentajes en `indicator_objective`; los cambios mensuales se reflejan de inmediato en **Indicadores General**. Cada creación, edición o eliminación crea una copia versionada en `indicator_objective_history` con mes, año, usuario y datos previos/posteriores. Admin y supervisor pueden administrar los objetivos y buscar por evaluado u objetivo. Ejecuta `flask --app run.py init-db` para crear las tablas y cargar los 48 objetivos iniciales.

El módulo incluye filtros por fechas, estado, prioridad, grupo, técnico, categoría y sitio en `Data`; los demás módulos tienen búsqueda, detalle de fila y exportación Excel del resultado filtrado. Cuenta con tarjetas KPI, gráficos, métricas de cobertura e historial de importación. La exportación se limita a 50.000 filas. Agentes pueden consultar y exportar, pero no cargar información. Solo administradores pueden depurar una copia histórica; esta acción elimina sus filas archivadas, conserva los registros operativos actuales y el resumen/auditoría de la importación.

Después de actualizar el código, crea las tablas y columnas históricas con `flask --app run.py init-db`. La migración agrega las nuevas columnas de forma compatible y crea la tabla de filas históricas.
