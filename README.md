# Extractor OCR — Destinatarios

Aplicación de **escritorio** (Python, PySide6) para extraer el texto del **destinatario** en fotos de etiquetas de sobres, usando **visión por IA** (OpenAI, por defecto `gpt-4o`). Los datos editados se **persisten en un backend FastAPI** (JWT + API REST); la clave de OpenAI solo se usa en el cliente para llamadas a la API de visión.

## Qué hace la app

- Carga una o varias imágenes (JPG, JPEG, PNG), lista y vista previa con zoom y recorte.
- Rotación, recorte libre o cuadrado 1:1, envío del recorte a la IA y formulario de campos estructurados.
- Registro por **sede** obligatoria: `AJUSCO` o `COYOACÁN`.
- **Exportación** por rango de fechas (CSV / Excel) con los datos obtenidos desde el backend.
- **Temas** desde el menú Ver; registro de actividad en `%LOCALAPPDATA%\ExtractorOCR\logs\extractor_ocr.log` (la app crea la carpeta automáticamente al iniciar).

## Requisitos

| Componente | Uso |
|--------------|-----|
| **Python 3.11+** | Intérprete y entorno virtual. |
| **Dependencias** | Ver `requirements.txt` (PySide6, OpenAI, httpx, pandas, etc.). |
| **Backend FastAPI** | Debe estar en marcha y accesible en `API_BASE_URL`. Al arrancar la app aparece **inicio de sesión** (usuario/contraseña); sin sesión válida no se abre la ventana principal. |
| **OpenAI** | `OPENAI_API_KEY` en `.env` para el botón **Enviar a IA**. |

## Instalación

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux / macOS

pip install -r requirements.txt
copy .env.example .env          # Windows; en Unix: cp .env.example .env
```

**Un solo entorno virtual:** usa solo la carpeta **`.venv`** en la raíz del repo (es la que ignora Git en `.gitignore`). Si además tienes una carpeta `venv/`, es redundante y suele confundir (dos activaciones distintas, dos `pip install`, etc.).

**Si PyInstaller u otras herramientas fallan con `C:\Python314\python.exe` no encontrado:** tus archivos `.venv\pyvenv.cfg` y `venv\pyvenv.cfg` guardan el intérprete **base** con el que se creó el entorno. Si Python se instaló o actualizó en otra ruta (p. ej. `...\AppData\Local\Programs\Python\Python314\`), esos venv quedan **rotos**. Solución: borra las carpetas `.venv` y `venv` (solo locales, no van al Git), y crea de nuevo **solo** `.venv` con el Python que sí exista, por ejemplo en PowerShell desde la raíz del proyecto:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Comprueba con `py -0p` qué versiones tienes y ajusta `-3.14` si usas otra.

Edita `.env` con al menos:

- URL del API y credenciales de uso habitual (ver tabla siguiente).
- `OPENAI_API_KEY` si vas a usar **Enviar a IA**.

No subas `.env` al repositorio; usa secretos solo en local o en tu gestor de despliegue.

## Variables de entorno

Resumen (valores por defecto en `app/config/settings.py`). La plantilla está en [`.env.example`](.env.example).

| Variable | Descripción |
|----------|-------------|
| `API_BASE_URL` | URL base del FastAPI **sin** barra final (ej. `http://127.0.0.1:8000`). |
| `LOGIN_ENDPOINT` | Ruta de login (por defecto `/auth/login`). |
| `REGISTROS_ENDPOINT` | Ruta de registros OCR (por defecto `/registros/`). |
| `API_TIMEOUT_SECONDS` | Timeout HTTP hacia el backend (segundos). |
| `OPENAI_API_KEY` | Clave para llamadas a OpenAI desde el cliente. |
| `OPENAI_MODEL` | Modelo (por defecto `gpt-4o`). |
| `TIMEOUT_SECONDS` | Timeout de llamadas a OpenAI. |
| `EXPORT_DIR` | Carpeta por defecto para exportaciones generadas en el cliente. |

### Persistencia desde el cliente

En **uso normal**, guardar listados y altas de extracciones va por **HTTP** al backend (`POST`/`GET` bajo `REGISTROS_ENDPOINT`), con el JWT obtenido en el login.

La app de escritorio no administra base de datos local ni motor SQL; actúa como cliente API-only.

## Ejecución

Desde la **raíz del repositorio** (donde está la carpeta `app/`):

```bash
python -m app.main
```

Asegúrate de que el backend responde en `API_BASE_URL` antes de iniciar sesión.

### Logs en Windows (desarrollo y producción)

La app escribe logs siempre en una ruta por usuario:

- `%LOCALAPPDATA%\ExtractorOCR\logs\extractor_ocr.log`

No necesitas crear la carpeta manualmente: la aplicación crea `ExtractorOCR\logs` al arrancar.

Para abrir la carpeta de logs en PowerShell:

```powershell
explorer "$env:LOCALAPPDATA\ExtractorOCR\logs"
```

Para seguir el log en tiempo real:

```powershell
Get-Content "$env:LOCALAPPDATA\ExtractorOCR\logs\extractor_ocr.log" -Wait
```

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

Las pruebas de persistencia usan mocks de API para validar el contrato del cliente sin depender de SQLite/MySQL local.

## Estructura del repositorio

```
app/
  main.py              # Entrada: logging, login, ventana principal
  api/                 # Clientes HTTP de autenticación y registros
  services/            # Casos de uso: OCR, auth, registros y exportación
  components/          # Widgets y paneles reutilizables de PySide6
  views/               # Ventanas principales y diálogos
  states/              # Sesión, caché de imágenes y workers
  models/              # Modelos de dominio y esquemas compartidos
  utils/               # Imagen, recorte y mapeos reutilizables
  config/              # Settings, variables de entorno y constantes
  assets/              # Iconos, imágenes y recursos de temas
  data/                # Directorio local para exports y datos de apoyo de la app
tests/
  unit/                # Tests unitarios
agents/                # Guías para agentes de IA en este repo
skills/
extraccion_ocr.py      # Script legacy por lotes (sin UI)
```

## Empaquetado e instalador

Para distribuir la app en Windows se recomienda generar primero una carpeta `--onedir` con PyInstaller y después crear un instalador con Inno Setup. Este flujo es más estable para PySide6 que `--onefile` y permite instalar todas las dependencias juntas.

### 1. Generar carpeta con PyInstaller

Desde la raíz del proyecto:

```powershell
.\.venv\Scripts\Activate.ps1

python -m PyInstaller `
  --noconfirm `
  --clean `
  --windowed `
  --onedir `
  --name "ExtractorOCR" `
  --icon ".\extractor_ocr.ico" `
  --paths "." `
  --add-data "app\assets;app\assets" `
  "app\main.py"
```

`--icon` solo pone el icono del `.exe` en el Explorador de Windows. Los iconos de la interfaz salen de las fuentes e imágenes en `app/assets` (sobre todo `app/assets/fonts/MaterialSymbolsOutlined.ttf`). `--add-data` las copia a `dist\ExtractorOCR\_internal\app\assets`. En PowerShell el `;` de `--add-data` tiene que ir **entre comillas**; si no, PowerShell lo interpreta como fin de comando.

El ejecutable queda en:

```text
dist\ExtractorOCR\ExtractorOCR.exe
```

Antes de crear el instalador, abre ese `.exe` y valida que la ventana de login aparezca **con iconos** (botones, menú y logo). Si faltan, revisa que exista `dist\ExtractorOCR\_internal\app\assets\fonts\MaterialSymbolsOutlined.ttf`. Si reutilizas `ExtractorOCR.spec`, también debe incluir esa carpeta en `datas`.

### 2. Crear instalador con Inno Setup

El script del instalador está en:

```text
installer\ExtractorOCR.iss
```

Abre **Inno Setup Compiler**, carga ese archivo y ejecuta **Build > Compile**. El instalador resultante se genera en:

```text
installer_output\Instalador_ExtractorOCR.exe
```

Con la configuración actual, la app se instala para el usuario actual en:

```text
C:\Users\Alfredo\AppData\Local\Programs\ExtractorOCR
```

Los logs no se guardan dentro de la carpeta instalada; la app los crea automáticamente en:

```text
%LOCALAPPDATA%\ExtractorOCR\logs\extractor_ocr.log
```

### 3. Variables de entorno

El instalador configura variables de usuario alineadas con [`.env.example`](.env.example): `API_BASE_URL`, `LOGIN_ENDPOINT`, `REGISTROS_ENDPOINT`, `COVERTURAS_ENDPOINT`, `ENVIOS_PX_ENDPOINT`, `API_TIMEOUT_SECONDS`, `OPENAI_MODEL`, `TIMEOUT_SECONDS` y `EXPORT_DIR`. `API_BASE_URL` queda en producción (`https://tools.feuh.com.mx`).

La clave `OPENAI_API_KEY` no debe incluirse en el instalador ni en el repositorio. Agrégala como variable de entorno de usuario en cada máquina:

```powershell
setx OPENAI_API_KEY "tu_clave_openai"
```

Después de agregarla, cierra y vuelve a abrir la app. Si la app ya estaba abierta, no verá la variable nueva hasta reiniciarse. Para verificarla en una nueva PowerShell:

```powershell
echo $env:OPENAI_API_KEY
```

No hace falta copiar `.env` junto al `.exe` si las variables de entorno ya están configuradas en Windows. Si cambias valores del instalador, recompila `installer\ExtractorOCR.iss` y vuelve a instalar.

## Script legacy

`extraccion_ocr.py` en la raíz conserva un flujo por **lotes** sin interfaz gráfica. La aplicación nueva reutiliza la idea de esquema JSON y campos de destinatario, alineada al contrato actual del producto.

## Documentación adicional

- Convenciones y agentes del repositorio: [AGENTS.md](AGENTS.md).
- Capa de datos del cliente API-only: `skills/data_access_layer.md`.


# Quitarlas de esta sesión
Remove-Item Env:API_BASE_URL -ErrorAction SilentlyContinue
Remove-Item Env:LOGIN_ENDPOINT -ErrorAction SilentlyContinue
Remove-Item Env:COVERTURAS_ENDPOINT -ErrorAction SilentlyContinue
Remove-Item Env:REGISTROS_ENDPOINT -ErrorAction SilentlyContinue