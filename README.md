# Extractor OCR — Destinatarios

Aplicación de **escritorio** (Python, PySide6) para extraer el texto del **destinatario** en fotos de etiquetas de sobres, usando **visión por IA** (OpenAI, por defecto `gpt-4o`). Los datos editados se **persisten en un backend FastAPI** (JWT + API REST); la clave de OpenAI solo se usa en el cliente para llamadas a la API de visión.

## Qué hace la app

- Carga una o varias imágenes (JPG, JPEG, PNG), lista y vista previa con zoom y recorte.
- Rotación, recorte libre o cuadrado 1:1, envío del recorte a la IA y formulario de campos estructurados.
- Registro por **sede** obligatoria: `AJUSCO` o `COYOACÁN`.
- **Exportación** por rango de fechas (CSV / Excel) según los datos disponibles desde el backend o el modo local de tests.
- **Temas** desde el menú Ver; registro de actividad en `logs/extractor_ocr.log` (carpeta `logs/` en la raíz del repositorio).

## Requisitos

| Componente | Uso |
|--------------|-----|
| **Python 3.11+** | Intérprete y entorno virtual. |
| **Dependencias** | Ver `requirements.txt` (PySide6, OpenAI, httpx, pandas, etc.). |
| **Backend FastAPI** | Debe estar en marcha y accesible en `API_BASE_URL`. Al arrancar la app aparece **inicio de sesión** (usuario/contraseña); sin sesión válida no se abre la ventana principal. |
| **OpenAI** | `OPENAI_API_KEY` en `.env` para el botón **Enviar a IA**. |
| **MySQL / SQLite (servidor)** | El almacenamiento definitivo de registros lo define **tu API** (p. ej. SQLite o MySQL en el servidor). La sección [Base de datos MySQL](#base-de-datos-mysql) y [docs/MYSQL_MIGRATION.md](docs/MYSQL_MIGRATION.md) sirven para operaciones de esquema y migración en el entorno de datos, no sustituyen el backend. |

## Instalación

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux / macOS

pip install -r requirements.txt
copy .env.example .env          # Windows; en Unix: cp .env.example .env
```

Edita `.env` con al menos:

- URL del API y credenciales de uso habitual (ver tabla siguiente).
- `OPENAI_API_KEY` si vas a usar **Enviar a IA**.

No subas `.env` al repositorio; usa secretos solo en local o en tu gestor de despliegue.

## Variables de entorno

Resumen (valores por defecto en código: `app/config.py`). La plantilla está en [`.env.example`](.env.example).

| Variable | Descripción |
|----------|-------------|
| `API_BASE_URL` | URL base del FastAPI **sin** barra final (ej. `http://127.0.0.1:8000`). |
| `LOGIN_ENDPOINT` | Ruta de login (por defecto `/auth/login`). |
| `REGISTROS_ENDPOINT` | Ruta de registros OCR (por defecto `/registros`). |
| `API_TIMEOUT_SECONDS` | Timeout HTTP hacia el backend (segundos). |
| `OPENAI_API_KEY` | Clave para llamadas a OpenAI desde el cliente. |
| `OPENAI_MODEL` | Modelo (por defecto `gpt-4o`). |
| `TIMEOUT_SECONDS` | Timeout de llamadas a OpenAI. |
| `EXPORT_DIR` | Carpeta por defecto para exportaciones generadas en el cliente. |
| `DB_ENGINE`, `DB_*` | Relevantes para **scripts** de MySQL y para código que acceda a BD local; ver [Base de datos MySQL](#base-de-datos-mysql). |

### Persistencia desde el cliente

En **uso normal**, guardar listados y altas de extracciones va por **HTTP** al backend (`POST`/`GET` bajo `REGISTROS_ENDPOINT`), con el JWT obtenido en el login.

Solo para **tests automatizados** (y escenarios muy concretos de desarrollo) se puede forzar repositorio local SQLite con la variable `OCR_USE_SQLITE_REPOSITORY=1` (no hace falta definirla en producción). Los tests fijan esto en `tests/conftest.py`.

## Ejecución

Desde la **raíz del repositorio** (donde está la carpeta `app/`):

```bash
python -m app.main
```

Asegúrate de que el backend responde en `API_BASE_URL` antes de iniciar sesión.

## Uso (flujo típico)

1. **Iniciar sesión** en el diálogo que aparece al arrancar (backend y usuario válidos).
2. **Abrir imágenes**: menú **Archivo → Abrir…** o botón equivalente en el panel izquierdo (JPG, JPEG, PNG).
3. **Seleccionar** una imagen en la lista.
4. **Rotar** si hace falta (menú **Edición** o controles del panel).
5. **Modo de recorte**: libre o cuadrado 1:1.
6. **Seleccionar región** en el visor (arrastrar con el botón izquierdo) y **Aplicar recorte**.
7. Elegir **SEDE**: `AJUSCO` o `COYOACÁN` (obligatorio para enviar/guardar).
8. **Enviar a IA** y revisar o editar campos en el panel derecho.
9. **Guardar registro** (botón en el panel derecho; el guardado va al backend salvo modo local de tests).
10. **Exportar** por fechas: **Archivo → Exportar…**.

## Controles del visor

- **Zoom**: rueda del ratón.
- **Pan**: botón central del ratón, o **mantener Espacio** y arrastrar con el botón izquierdo.
- **Selección de recorte**: arrastrar con el botón izquierdo (sin Espacio).
- **Ajustar imagen a la ventana**: **Ver → Ajustar a ventana** (misma acción base que restablecer la vista al encajar el contenido).

## Atajos de teclado

| Atajo | Acción |
|-------|--------|
| **Ctrl+O** | Abrir imágenes (atajo estándar del sistema). |
| **Ctrl+E** | Exportar… |
| **Ctrl+L** | Rotar 90° a la izquierda. |
| **Ctrl+R** | Rotar 90° a la derecha. |
| **Ctrl+0** | Restablecer zoom / vista. |
| **Ctrl++** / **Ctrl+-** | Zoom in / out (menú Ver). |

El guardado de registro no tiene atajo asignado; se hace con el botón **Guardar registro**.

## Smoke test manual

1. Tener el **backend** disponible y un usuario de prueba.
2. Arrancar `python -m app.main` e **iniciar sesión**.
3. Abrir una imagen de prueba y seleccionarla en la lista.
4. Rotar si procede; trazar recorte y aplicar.
5. Seleccionar **SEDE**.
6. **Enviar a IA** (requiere `OPENAI_API_KEY` válida).
7. Revisar campos, editar si hace falta y **Guardar registro**.
8. **Archivo → Exportar…** y comprobar el archivo generado.

## Tests

```bash
pip install pytest
pytest tests/ -v
```

En `tests/conftest.py` se fuerza `DB_ENGINE=sqlite` y `OCR_USE_SQLITE_REPOSITORY=1` para que los tests no dependan de MySQL ni del servidor FastAPI al insertar o listar en local.

## Base de datos MySQL

Procedimiento orientado al **entorno de datos** (servidor, migraciones, comprobaciones). Los pasos concretos y el troubleshooting están en **[docs/MYSQL_MIGRATION.md](docs/MYSQL_MIGRATION.md)**.

1. Crear la base `tools_OCR` (o la que uses) en el servidor.
2. `python scripts/create_mysql_schema.py` o importar `sql/schema_mysql.sql`.
3. Opcional: migrar desde SQLite con `python scripts/migrate_sqlite_to_mysql.py` (revisar `--dry-run`).
4. Configurar `DB_ENGINE=mysql` y variables `DB_*` donde corresponda (p. ej. servidor del backend o scripts).
5. Comprobar conectividad: `python scripts/check_db.py`.

## Estructura del repositorio

```
app/
  main.py              # Entrada: logging, login, ventana principal
  config.py            # Variables de entorno y rutas
  ui/                  # PySide6: ventanas, paneles, visor, temas
  core/                # IA, cliente HTTP, repositorio, exportación, recorte, modelos
  data/                # SQLite local de desarrollo (ruta por defecto), exports por defecto
sql/                   # Esquema MySQL
scripts/               # create_mysql_schema, migrate_sqlite_to_mysql, check_db
docs/                  # MYSQL_MIGRATION.md, etc.
tests/
  unit/                # Tests unitarios
agents/                # Guías para agentes de IA en este repo
skills/
extraccion_ocr.py      # Script legacy por lotes (sin UI)
```

## Empaquetado (PyInstaller)

`pyinstaller` está referenciado en `requirements.txt`. Ejemplo mínimo (desde la raíz del proyecto):

```bash
pyinstaller --name ExtractorOCR --windowed --onefile app/main.py
```

Si al ejecutar el binario faltan módulos del paquete `app`, amplía el comando con [`--hidden-import`](https://pyinstaller.org/en/stable/usage.html) o un archivo `.spec` que recoja submódulos y datos estáticos que uses.

## Script legacy

`extraccion_ocr.py` en la raíz conserva un flujo por **lotes** sin interfaz gráfica. La aplicación nueva reutiliza la idea de esquema JSON y campos de destinatario, alineada al contrato actual del producto.

## Documentación adicional

- Convenciones y agentes del repositorio: [AGENTS.md](AGENTS.md).
- Estrategia InnoDB / capa de datos: `skills/db_strategy_innodb.md`, `skills/data_access_layer.md`.
