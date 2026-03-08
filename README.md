# Extractor OCR - Destinatarios

Aplicación de escritorio en Python para extraer el texto del **DESTINATARIO** en etiquetas de sobres usando visión por IA (OpenAI GPT-4o).

## Requisitos

- Python 3.11+
- Clave API de OpenAI (`OPENAI_API_KEY` en `.env`)

## Instalación

```bash
# Crear entorno virtual
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # Linux/macOS

# Instalar dependencias
pip install -r requirements.txt

# Copiar y configurar .env
copy .env.example .env
# Editar .env y añadir OPENAI_API_KEY=sk-...
```

## Ejecución

```bash
python -m app.main
```

O desde la raíz del proyecto:

```bash
python -m app.main
```

## Uso

1. **Abrir imágenes**: Archivo → Abrir… (JPG, JPEG, PNG).
2. **Seleccionar imagen** en la lista izquierda.
3. **Rotar** si hace falta (90° izq/der).
4. **Modo de recorte**: libre o cuadrado 1:1.
5. **Seleccionar región** con el ratón (arrastrar).
6. **Aplicar recorte**.
7. **Seleccionar SEDE**: AJUSCO | COYOACÁN (obligatorio).
8. **Enviar a IA** para extraer campos.
9. **Revisar/editar** el resultado y **Guardar registro**.
10. **Exportar** registros por rango de fechas (Archivo → Exportar).

## Controles del visor

- **Zoom**: rueda del ratón.
- **Pan**: botón central o Espacio + arrastre.
- **Selección**: arrastrar con botón izquierdo.
- **Ajustar ventana**: Ver → Ajustar a ventana.
- **Reset zoom**: Ctrl+0.

## Atajos

- Ctrl+O: Abrir
- Ctrl+E: Exportar
- Ctrl+S: Guardar
- Ctrl+L: Rotar 90° izq.
- Ctrl+R: Rotar 90° der.
- Ctrl+0: Restablecer zoom

## Smoke test (manual)

1. Abrir una imagen de prueba.
2. Seleccionarla en la lista.
3. Rotar si procede.
4. Trazar un recorte y aplicar.
5. Seleccionar SEDE.
6. Enviar a IA (requiere API key válida).
7. Revisar campos, editar si hace falta.
8. Guardar registro.
9. Exportar (Archivo → Exportar).

## Tests

```bash
pip install pytest
pytest tests/ -v
```

## Estructura

```
app/
  main.py           # Entrada
  config.py         # Configuración
  ui/               # Interfaz PySide6
  core/             # Lógica: IA, BD, recorte, exportación
  data/             # SQLite, exports
tests/
  unit/             # Tests unitarios
```

## Empaquetado (PyInstaller)

```bash
pip install pyinstaller
pyinstaller --name ExtractorOCR --windowed --onefile app/main.py
```

## Script legacy

El script original `extraccion_ocr.py` sigue en la raíz para procesamiento por lotes sin UI. La nueva app reutiliza la lógica de prompts y esquema JSON, adaptada a la especificación actual.
