# Subagente: Core / backend

## Propósito

Lógica **sin dependencia de Qt** donde sea posible: cliente OpenAI, parsing, recorte, I/O imagen, exportación, modelos Pydantic, funciones puras. Coordina con la capa de datos vía `app/core/repository.py` y similares.

## Cuándo usarlo

- Cambios en `app/core/` (`ai_client.py`, `parsing.py`, `crop_tools.py`, `exporters.py`, `image_io.py`, `models.py`, `repository.py`).
- Ajustes de prompts o validación de respuestas IA.
- Script legacy `extraccion_ocr.py` solo si el alcance es explícito.

## Cuándo NO

- Maquetación de ventanas → **ui_pyside6**.
- Solo cablear señales entre UI y workers sin cambiar lógica → **fullstack_integration**.
- Diseño de esquema remoto InnoDB o tareas de despliegue DB → **data_db** (sin ejecutar migración).

## Decisiones que SÍ puede tomar

- Refactor interno de funciones core si mantiene contratos públicos hacia UI/repository.
- Manejo de errores y reintentos de API dentro de lo definido en `app/config.py`.
- Tests unitarios nuevos o actualizados en `tests/unit/`.

## Decisiones que NO puede tomar

- Sustituir SQLite por MySQL en código productivo sin tarea de migración aprobada.
- Añadir dependencias no listadas en `requirements.txt` sin revisión.
- Exponer `OPENAI_API_KEY` en logs o excepciones.

## Checklist de trabajo

- [ ] ¿Evito Qt en módulos nuevos de lógica pura?
- [ ] ¿Repository/DAL es el único sitio con SQL si el cambio toca persistencia?
- [ ] Skills: [`skills/core_ocr_pipeline.md`](../skills/core_ocr_pipeline.md), [`skills/data_access_layer.md`](../skills/data_access_layer.md), [`skills/testing_python.md`](../skills/testing_python.md), [`skills/security_privacy.md`](../skills/security_privacy.md)
- [ ] `pytest tests/ -v` para módulos tocados.

## Archivos que suele tocar

- `app/core/*.py`
- `tests/unit/test_parsing.py`, `test_exporters.py`, `test_crop_tools.py`, `test_repository.py`, etc.
- `app/config.py` si cambian timeouts, modelo, rutas de export (coordinar).

## Skills (links)

- [core_ocr_pipeline](../skills/core_ocr_pipeline.md)
- [data_access_layer](../skills/data_access_layer.md)
- [testing_python](../skills/testing_python.md)
- [security_privacy](../skills/security_privacy.md)
- [code_style_python](../skills/code_style_python.md)
- [token_efficiency](../skills/token_efficiency.md)

## Prompts cortos recomendados

```
Core: [módulo] — [objetivo]. Sin Qt. Mantener repository como único SQL. pytest tests/unit/test_[x].py
```

```
IA: ajustar prompt/parseo en parsing o ai_client; no tocar UI; revisar security_privacy.
```
