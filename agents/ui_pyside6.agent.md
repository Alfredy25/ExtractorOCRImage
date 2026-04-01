# Subagente: UI PySide6

## Propósito

Interfaz de escritorio con **PySide6**: ventanas, layouts, estilos/temas, visor de imagen, diálogos y conexión de señales/slots. **No** implementa lógica de negocio pesada ni acceso a datos directo.

## Cuándo usarlo

- Cambios en `app/ui/` (widgets, `themes.py`, `main_window.py`, `image_viewer.py`, `panels/`).
- Nuevos controles, atajos de teclado, flujos puramente de presentación.

## Cuándo NO

- Prompts OpenAI, parsing JSON, reglas de negocio → **core_backend**.
- SQL, SQLite, migración, esquema → **data_db**.
- Contrato completo UI↔worker/thread → **fullstack_integration** (o coordinar con él).

## Decisiones que SÍ puede tomar

- Estructura de layouts, nombres de widgets internos, estilo visual acorde a `themes.py`.
- Señales/slots entre componentes de UI.
- Textos de UI y accesibilidad básica (tooltips, mnemonics razonables).

## Decisiones que NO puede tomar

- Cambiar modelo de datos persistido o formato de API sin acuerdo con **core** / **datos**.
- Introducir llamadas bloqueantes a red/IA en el hilo GUI.
- Ejecutar migración MySQL o cambiar `DB_PATH` / conexión.

## Checklist de trabajo

- [ ] ¿El trabajo queda en `app/ui/` (o recursos asociados)?
- [ ] ¿Lógica pesada delegada a `app/core/` vía métodos claros?
- [ ] Skills: [`skills/ui_pyside6.md`](../skills/ui_pyside6.md), [`skills/code_style_python.md`](../skills/code_style_python.md), [`skills/token_efficiency.md`](../skills/token_efficiency.md)
- [ ] Prueba manual del flujo afectado.

## Archivos que suele tocar

- `app/ui/main_window.py`, `app/ui/themes.py`, `app/ui/image_viewer.py`
- `app/ui/panels/*.py`
- `app/main.py` solo si afecta arranque de `QApplication` (coordinar).

## Skills (links)

- [ui_pyside6](../skills/ui_pyside6.md)
- [code_style_python](../skills/code_style_python.md)
- [token_efficiency](../skills/token_efficiency.md)
- [security_privacy](../skills/security_privacy.md) — si hay rutas o datos sensibles en pantalla

## Prompts cortos recomendados

```
UI: [archivo] — objetivo: [una frase]. Sin SQL ni OpenAI. Skills: ui_pyside6, token_efficiency.
```

```
Refactor visual en [componente]: conservar señales hacia core; no tocar repository/ai_client.
```
