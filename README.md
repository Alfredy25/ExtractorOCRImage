# Extractor OCR — Destinatarios

Aplicación de **escritorio** (Python, PySide6) para extraer el texto del **destinatario** en fotos de etiquetas de sobres, usando **visión por IA** (OpenAI, por defecto `gpt-4o`). Los datos editados se **persisten en un backend FastAPI** (JWT + API REST); la clave de OpenAI solo se usa en el cliente para llamadas a la API de visión. Además permite **crear y consultar envíos Paquetexpress**, consultar **coberturas** por código postal y **exportar** esos envíos a Excel con el layout listo para importar en Paquetexpress.

## Qué hace la app

- Carga una o varias imágenes (JPG, JPEG, PNG), lista y vista previa con zoom y recorte.
- Rotación, recorte libre o cuadrado 1:1, envío del recorte a la IA y formulario de campos estructurados.
- Registro por **sede** obligatoria: `AJUSCO` o `COYOACÁN`.
- **Búsqueda de destinatarios** en el directorio (`RECEIVERS_ENDPOINT`) con filtros, orden y paginación, antes de extraer la foto.
- **Exportación** por rango de fechas (CSV / Excel) con los datos obtenidos desde el backend.
- **Envíos Paquetexpress**: consulta de cobertura por CP (API `COVERTURAS_ENDPOINT`), creación/edición de envíos y listado vía `ENVIOS_PX_ENDPOINT`.
- **Exportación de envíos** a Excel con columnas y formato preparados para carga en Paquetexpress (desde **Ver envíos**).
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
| `COVERTURAS_ENDPOINT` | Ruta de coberturas Paquetexpress (por defecto `/coverages/`). |
| `ENVIOS_PX_ENDPOINT` | Ruta de envíos Paquetexpress (por defecto `/shipments-px/`). |
| `RECEIVERS_ENDPOINT` | Ruta del directorio de destinatarios (por defecto `/receivers/`). |
| `ADDRESSES_ENDPOINT` | Domicilios de destinatarios (por defecto `/addresses/`). |
| `CONTACTS_ENDPOINT` | Contactos (por defecto `/contacts/`). |
| `TITLES_ENDPOINT` | Títulos / cargos (por defecto `/titles/`). |
| `JOB_ROLES_ENDPOINT` | Puestos (por defecto `/job-roles/`). |
| `ORGANIZATIONS_ENDPOINT` | Organizaciones (por defecto `/organizations/`). |
| `VOLANTES_ENDPOINT` | Volantes (por defecto `/volante/`). |
| `SEPOMEX_ENDPOINT` | Catálogo SEPOMEX (por defecto `/sepomex/`). |
| `API_TIMEOUT_SECONDS` | Timeout HTTP hacia el backend (segundos). |
| `OPENAI_API_KEY` | Clave para llamadas a OpenAI desde el cliente. |
| `OPENAI_MODEL` | Modelo (por defecto `gpt-6-luna`). |
| `TIMEOUT_SECONDS` | Timeout de llamadas a OpenAI. |
| `EXPORT_DIR` | Carpeta por defecto para exportaciones generadas en el cliente. |

### Persistencia desde el cliente

En **uso normal**, guardar listados y altas de extracciones va por **HTTP** al backend (`POST`/`GET` bajo `REGISTROS_ENDPOINT`), con el JWT obtenido en el login.

Los **envíos Paquetexpress** también van por API: alta/consulta/actualización bajo `ENVIOS_PX_ENDPOINT` y consulta de coberturas bajo `COVERTURAS_ENDPOINT` (por código postal).

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
7. **Buscar al destinatario** en la sección **Destinatario** del inspector, leyendo el nombre en la foto. Todavía no hay OCR.
8. Si aparece, elegir uno de sus domicilios y pulsar **Crear envío con este destinatario** (ver sección siguiente).
9. Si no aparece, desplegar **Datos extraídos**, elegir **SEDE** (`AJUSCO` o `COYOACÁN`), **Enviar a IA** y revisar o editar los campos.
10. **Consultar cobertura** con el código postal del OCR y completar el alta de destinatario y envío.
11. **Guardar registro** (botón del inspector; solo se habilita cuando hay datos OCR que guardar).
12. **Exportar** registros por fechas: **Archivo → Exportar…** (o el ítem de navegación **Exportar registros**).
13. (Opcional) **Ver envíos**: consultar el historial por rango de fechas y **exportar a Excel** listo para Paquetexpress.

## Envíos Paquetexpress

El flujo completo está documentado en [`docs/flows/flow_create_shipment_px.md`](docs/flows/flow_create_shipment_px.md). El inspector del Workspace tiene dos secciones plegables, una por rama: se busca al destinatario **antes** de extraer, y el OCR solo entra en juego cuando la búsqueda no encuentra nada.

### Rama A: el destinatario ya existe

1. En **Destinatario**, buscar por nombre de la persona o de la organización, o dejar el cuadro vacío y usar solo tipo, estado y orden. La consulta arranca en página 1, 10 por página, ordenada por `id` ascendente, y se puede paginar.
2. Elegir el destinatario y uno de sus domicilios. Si solo tiene uno, queda elegido. **Añadir nuevo volante** solo le enlaza otro número: un destinatario puede tener varios.
3. Pulsar **Crear envío con este destinatario**: se abre **Crear envío Paquetexpress** con la **imagen del recorte** como referencia, sin campos OCR.
4. La ventana consulta `COVERTURAS_ENDPOINT` con el **código postal del domicilio**. Si no hay cobertura, avisa, se cierra y no queda registro OCR.
5. Con cobertura: elegir colonia, completar paquete, RFC y comentarios, y confirmar (`POST` a `ENVIOS_PX_ENDPOINT`).

En esta rama no se extrae la foto, así que tampoco hay registro OCR que guardar.

### Rama B: el destinatario no existe

1. La búsqueda sin coincidencias despliega sola la sección **Datos extraídos**.
2. Elegir **SEDE** y pulsar **Enviar a IA**; revisar o corregir los campos.
3. Pulsar **Consultar cobertura**: la app consulta `COVERTURAS_ENDPOINT` con el **CP del OCR**. Si no hay cobertura, no se abre la creación ni se da de alta al destinatario; solo queda **Guardar registro**.
4. Con cobertura se abre **Crear envío Paquetexpress** con las coberturas, los campos OCR de solo lectura y el alta de destinatario. Esta pantalla ya no vuelve a buscar.
5. **Dar de alta destinatario** abre el formulario precargado con el OCR (`POST` a `RECEIVERS_ENDPOINT`, con su domicilio en la misma petición). El número de volante escrito a mano en la extracción aparece en la referencia y queda en el volante inicial. Si responde 409, se reutiliza el destinatario existente.
6. Completar paquete, RFC y comentarios y confirmar el envío.
7. De vuelta en el Workspace, pulsar **Guardar registro** para persistir la extracción.

### Consultar y exportar envíos

1. En la barra lateral, abre **Ver envíos** (ventana **Historial de Envíos**).
2. Elige rango de **fecha/hora** y pulsa **Consultar**: los datos vienen de `GET` sobre `ENVIOS_PX_ENDPOINT`.
3. Revisa la tabla (paginada); puedes **Editar** un envío seleccionado (vuelve a consultar cobertura si cambias datos sensibles como la colonia).
4. **Exportar a Excel** genera un `.xlsx` con columnas y formato alineados al layout de importación de Paquetexpress (nombre sugerido `envios_DD-MM-YYYY.xlsx`).

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
5. (Rama A) Buscar un destinatario que exista, elegir domicilio y **Crear envío con este destinatario**; comprobar que la ventana muestra el recorte y la cobertura del CP del domicilio.
6. (Rama A) Completar paquete y confirmar; al volver al Workspace, **Guardar registro** debe seguir deshabilitado.
7. (Rama B) Buscar un nombre que no exista y comprobar que **Datos extraídos** se despliega solo.
8. (Rama B) Seleccionar **SEDE** y **Enviar a IA** (requiere `OPENAI_API_KEY` válida).
9. (Rama B) **Consultar cobertura** con el CP del OCR, dar de alta al destinatario y crear el envío.
10. (Rama B) De vuelta en el Workspace, revisar campos y **Guardar registro**.
11. **Archivo → Exportar…** y comprobar el archivo generado.
12. (Envíos) **Ver envíos** → consultar por fechas → **Exportar a Excel** y abrir el archivo generado.

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
  api/                 # Clientes HTTP: auth, registros, coberturas y envíos PX
  services/            # Casos de uso: OCR, auth, registros, Paquetexpress y exportación
  components/          # Widgets y paneles reutilizables de PySide6
  views/               # Ventanas principales, envíos, historial y diálogos
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

Abre **Inno Setup Compiler**, carga ese archivo y ejecuta **Build > Compile**. El instalador resultan~~t~~e se genera en:

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

El instalador configura variables de usuario alineadas con [`.env.example`](.env.example): `API_BASE_URL`, `LOGIN_ENDPOINT`, `REGISTROS_ENDPOINT`, `COVERTURAS_ENDPOINT`, `ENVIOS_PX_ENDPOINT`, `RECEIVERS_ENDPOINT`, `ADDRESSES_ENDPOINT`, `CONTACTS_ENDPOINT`, `TITLES_ENDPOINT`, `JOB_ROLES_ENDPOINT`, `ORGANIZATIONS_ENDPOINT`, `VOLANTES_ENDPOINT`, `SEPOMEX_ENDPOINT`, `API_TIMEOUT_SECONDS`, `OPENAI_MODEL`, `TIMEOUT_SECONDS` y `EXPORT_DIR`. `API_BASE_URL` queda en producción (`https://tools.feuh.com.mx`).

La clave `OPENAI_API_KEY` no debe incluirse en el instalador ni en el repositorio. Agrégala como variable de entorno de usuario en cada máquina:

```powershell
setx OPENAI_API_KEY "tu_clave_openai"
```

Después de agregarla, cierra y vuelve a abrir la app. Si la app ya estaba abierta, no verá la variable nueva hasta reiniciarse. Para verificarla en una nueva PowerShell:

```powershell
echo $env:OPENAI_API_KEY
```

Tras instalar, las variables nuevas no las ven los procesos que ya estaban en ejecución. Cierra por completo Extractor OCR y vuelve a abrirlo para que tome `API_BASE_URL`, los endpoints y el resto de variables de usuario. Si el instalador ofrece abrir la aplicación al terminar, es normal que el primer intento de sesión falle o use valores viejos: cierra esa ventana, abre de nuevo desde el menú Inicio y debería funcionar. En casos puntuales puede hacer falta cerrar sesión de Windows o reiniciar el equipo; el instalador usa `ChangesEnvironment=yes` para avisar al sistema, pero no siempre basta para procesos ya abiertos.

No hace falta copiar `.env` junto al `.exe` si las variables de entorno ya están configuradas en Windows. Si cambias valores del instalador, recompila `installer\ExtractorOCR.iss` y vuelve a instalar.

## Script legacy

`extraccion_ocr.py` en la raíz conserva un flujo por **lotes** sin interfaz gráfica. La aplicación nueva reutiliza la idea de esquema JSON y campos de destinatario, alineada al contrato actual del producto.

## Documentación adicional

- Convenciones y agentes del repositorio: [AGENTS.md](AGENTS.md).
- Capa de datos del cliente API-only: `skills/data_access_layer.md`.

## Una vez hecho lo anterior instalar la aplicación actual siguiendo estos pasos

- Desinstalar la aplicación anterior
- Quitar las variables de entorno con el siguiente código abriendo la terminal de powershell como administrador
  ```powershell
  $names = @(
    'API_BASE_URL','LOGIN_ENDPOINT','REGISTROS_ENDPOINT','COVERTURAS_ENDPOINT',
    'ENVIOS_PX_ENDPOINT','API_TIMEOUT_SECONDS','OPENAI_MODEL','TIMEOUT_SECONDS','EXPORT_DIR'
  )

  "=== Usuario ==="
  $names | ForEach-Object { "{0}={1}" -f $_, [Environment]::GetEnvironmentVariable($_, 'User') }

  "=== Máquina ==="
  $names | ForEach-Object { "{0}={1}" -f $_, [Environment]::GetEnvironmentVariable($_, 'Machine') }


  $names = @(
    'API_BASE_URL','LOGIN_ENDPOINT','REGISTROS_ENDPOINT','COVERTURAS_ENDPOINT',
    'ENVIOS_PX_ENDPOINT','API_TIMEOUT_SECONDS','OPENAI_MODEL','TIMEOUT_SECONDS','EXPORT_DIR'
  )

  foreach ($n in $names) {
    [Environment]::SetEnvironmentVariable($n, $null, 'User')
    [Environment]::SetEnvironmentVariable($n, $null, 'Machine')
  }
  ```
- Ejecutar el nuevo instalador creado con Inno Setup
- Iniciar Session

## Al programar quitarlas de esta sesión las variables de entorno

```powershell
Remove-Item Env:API_BASE_URL -ErrorAction SilentlyContinue
Remove-Item Env:LOGIN_ENDPOINT -ErrorAction SilentlyContinue
Remove-Item Env:COVERTURAS_ENDPOINT -ErrorAction SilentlyContinue
Remove-Item Env:REGISTROS_ENDPOINT -ErrorAction SilentlyContinue
Remove-Item Env:OPENAI_MODEL -ErrorAction SilentlyContinue
```
