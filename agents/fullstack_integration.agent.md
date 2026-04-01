# Subagente: Integración full‑stack

## Propósito

**Orquestar** la aplicación: contratos entre UI y core, flujos en `MainWindow`, uso de hilos/workers para no bloquear el GUI, manejo de errores en el límite UI↔negocio. Minimiza acoplamiento y evita duplicar reglas ya en skills.

## Cuándo usarlo

- Cambios que cruzan `app/ui/main_window.py` (o paneles) **y** `app/core/` en el mismo flujo.
- Introducir o modificar llamadas async/hilo para OpenAI o I/O pesado.
- Definir DTOs o métodos “fachada” entre capas.

## Cuándo NO

- Solo estilos o un widget aislado → **ui_pyside6**.
- Solo algoritmo de parsing o cliente HTTP → **core_backend**.
- Solo consultas SQL o diseño de tablas → **data_db**.

## Decisiones que SÍ puede tomar

- Dónde se invoca core desde UI (siempre fuera del hilo GUI para trabajo pesado).
- Mensajes de error unificados mostrados al usuario (texto de UI).
- Firma de callbacks/señales entre capas.

## Decisiones que NO puede tomar

- Cambiar esquema de base de datos o motor sin **data_db** y sin tarea explícita.
- Incrustar SQL en widgets.
- Decidir migración a MySQL: solo preparar interfaces si se pide explícitamente.

## Checklist de trabajo

- [ ] ¿El hilo GUI permanece libre de bloqueos de red/disco pesado?
- [ ] ¿Los errores de core se traducen a mensajes UI sin filtrar secretos?
- [ ] Skills: [`skills/ui_pyside6.md`](../skills/ui_pyside6.md) (límites UI), [`skills/core_ocr_pipeline.md`](../skills/core_ocr_pipeline.md), [`skills/token_efficiency.md`](../skills/token_efficiency.md), [`skills/testing_python.md`](../skills/testing_python.md)
- [ ] Smoke manual: abrir imagen → flujo hasta guardar/export según alcance.

## Archivos que suele tocar

- `app/ui/main_window.py`, `app/ui/panels/*.py` (wiring)
- Posiblemente `app/main.py` (política DPI / arranque)
- Punto de contacto con `app/core/` sin meter lógica de negocio en la vista

## Skills (links)

- [ui_pyside6](../skills/ui_pyside6.md)
- [core_ocr_pipeline](../skills/core_ocr_pipeline.md)
- [data_access_layer](../skills/data_access_layer.md)
- [testing_python](../skills/testing_python.md)
- [security_privacy](../skills/security_privacy.md)
- [token_efficiency](../skills/token_efficiency.md)

## Prompts cortos recomendados

```
Integración: flujo [nombre] — UI llama a core sin bloquear GUI; listar archivos a tocar.
```

```
Wiring: MainWindow + [panel] — señales hacia [función core]; manejo de error usuario.
```
