# Sistema de agentes — Extractor OCR

## Visión general

Este repositorio usa **agentes especializados** (definidos en `agents/`) y **skills reutilizables** (`skills/`) para que Cursor y otros asistentes trabajen con **responsabilidad única**, **menos tokens** y **menos ambigüedad**.

- **Entrada de la app**: `python -m app.main`
- **Stack**: Python 3.11+, PySide6, cliente HTTP hacia API REST (FastAPI/JWT).

Los subagentes **no duplican reglas**: delegan en skills. Antes de tareas grandes, elige el subagente adecuado y abre los skills enlazados.

---

## Principios de diseño

| Principio | Significado aquí |
|-----------|------------------|
| **Single responsibility** | Un cambio = un subagente principal; cruces mínimos UI ↔ core. |
| **Token efficiency** | Skills con checklists; prompts cortos; evitar pegar el repo entero. |
| **Explícito sobre implícito** | Límites de decisión en cada `.agent.md`; persistencia del cliente se resuelve por contrato API REST. |
---

## Subagentes (cuándo usar cuál)

| Subagente | Rol | Archivo |
|-----------|-----|---------|
| **UI PySide6** | Ventanas, widgets, temas, señales/slots, accesibilidad básica. | [`agents/ui_pyside6.agent.md`](agents/ui_pyside6.agent.md) |
| **Core / backend** | IA (OpenAI), parsing, recorte, exporters, lógica sin Qt. | [`agents/core_backend.agent.md`](agents/core_backend.agent.md) |
| **Integración full‑stack** | Contratos UI↔core, hilos/async, wiring en `main_window`, flujos end‑to‑end. | [`agents/fullstack_integration.agent.md`](agents/fullstack_integration.agent.md) |
| **Datos / API** | Contratos de persistencia por API REST, payloads y errores de sesión/HTTP. | [`agents/data_db.agent.md`](agents/data_db.agent.md) |

**Cuándo NO forzar subagentes**: cambios triviales de una línea o solo documentación pueden hacerse sin invocar un rol; igual conviene alinear el skill de estilo.

---

## Flujo de colaboración

```mermaid
flowchart LR
  UI[ui_pyside6]
  CORE[core_backend]
  INT[fullstack_integration]
  DATA[data_db]

  INT --> UI
  INT --> CORE
  CORE --> DATA
  UI -.->|eventos / resultados| INT
```

1. **Feature con pantalla nueva o flujo nuevo** → empieza **Integración** (contrato); luego **UI** o **Core** según dónde caiga el grueso del trabajo.
2. **Solo lógica / IA / export** → **Core**; tocar **Datos** si cambia el contrato de persistencia API.
3. **Solo widgets/temas** → **UI** sin tocar SQL; la UI solo consume servicios de API.

---

## Mapa subagentes ↔ skills

| Skill | UI | Core | Integración | Datos |
|-------|:--:|:----:|:-------------:|:-----:|
| [`skills/ui_pyside6.md`](skills/ui_pyside6.md) | ● | | ○ | |
| [`skills/core_ocr_pipeline.md`](skills/core_ocr_pipeline.md) | | ● | ○ | ○ |
| [`skills/data_access_layer.md`](skills/data_access_layer.md) | | ○ | ○ | ● |
| [`skills/testing_python.md`](skills/testing_python.md) | ○ | ○ | ● | ○ |
| [`skills/security_privacy.md`](skills/security_privacy.md) | ○ | ● | ● | ● |
| [`skills/token_efficiency.md`](skills/token_efficiency.md) | ● | ● | ● | ● |
| [`skills/code_style_python.md`](skills/code_style_python.md) | ● | ● | ● | ● |

● = aplica con frecuencia · ○ = aplica si el cambio lo exige

---

## Convenciones del repo

### Alcance de cambios

- Tocar solo archivos necesarios; no refactor masivo no solicitado.
- **UI**: `app/components/` (widgets) y `app/views/` (ventanas y diálogos).
- **Negocio**: `app/services/`; clientes HTTP en `app/api/`, modelos en `app/models/`.
- **Estado y utilidades**: `app/states/` y `app/utils/`.
- **Config**: `app/config/` — cambios coordinados con quien use esos settings o constantes.
- **Legacy**: `extraccion_ocr.py` — solo si el alcance lo pide; no divergir del contrato de la app sin motivo.

### Definition of Done

- [ ] Comportamiento acordado implementado sin romper flujos existentes.
- [ ] Sin secretos en código o commits; `.env` local.
- [ ] Tests relevantes actualizados o nuevos (`pytest tests/ -v` donde aplique).
- [ ] Si afecta persistencia: contrato API y mapeos cliente-servidor validados.

### Testing mínimo

- Ejecutar `pytest tests/ -v` tras cambios en core o datos.
- UI: `python scripts/preview_ui.py` renderiza las tres pantallas sin abrir ventanas y comprueba interacciones (clics del HUD, recorte, cobertura); deja capturas para revisar el resultado visual.
- UI: prueba manual mínima del flujo (abrir imagen, recorte, enviar, guardar) cuando se toque flujo crítico.

### Secretos y configuración

- `OPENAI_API_KEY` y similares vía `.env`; ver [`skills/security_privacy.md`](skills/security_privacy.md).

---

## Persistencia API-only

- El cliente de escritorio no maneja motor SQL ni esquema de base de datos.
- Guardado y consulta pasan por `app/api/` y `app/services/registros_service.py`.
- Cualquier cambio de persistencia debe expresarse como cambio de contrato REST, no como migración local.
- Referencia operativa: [`skills/data_access_layer.md`](skills/data_access_layer.md).

---

## Inicio rápido para un agente

1. Identificar subagente → abrir su `agents/*.agent.md`.
2. Cargar skills marcados allí (y tabla arriba).
3. Usar prompts cortos del skill `token_efficiency`.
4. Cerrar con DoD y pytest cuando corresponda.
