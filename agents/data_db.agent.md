# Subagente: Datos / API

## Propósito

**Capa de acceso a datos del cliente** mediante API REST: contratos de payload, normalización de campos y manejo de errores HTTP/sesión.

## Cuándo usarlo

- Cambios en `app/services/registros_service.py` o `app/api/registros_api.py`.
- Ajustes de payload/normalización entre UI y backend (`sede`, opcionales, tipos).
- Tests en `tests/unit/test_repository.py`.

## Cuándo NO

- Rediseño de widgets → **ui_pyside6**.
- Algoritmos de OCR/parsing sin tocar persistencia → **core_backend**.
- Solo cablear botones → **fullstack_integration**.

## Decisiones que SÍ puede tomar

- Consultas y transacciones en SQLite dentro del repositorio/DAL.
- Refactor para centralizar integración REST en una sola fachada de servicio.
- Definir convenciones de mapeo cliente↔backend y errores de sesión en servicios.

## Decisiones que NO puede tomar

- **No** introducir persistencia local SQL en el cliente.
- **No** mover lógica de contrato API a widgets de UI.
- **No** exponer credenciales o tokens en código o `.env` versionado.

## Checklist de trabajo

- [ ] ¿Toda persistencia vive en `app/api` + `app/services`, no en UI?
- [ ] ¿Tests de repositorio actualizados?
- [ ] Skills: [`skills/data_access_layer.md`](../skills/data_access_layer.md), [`skills/security_privacy.md`](../skills/security_privacy.md), [`skills/testing_python.md`](../skills/testing_python.md)
- [ ] `pytest tests/unit/test_repository.py -v`

## Archivos que suele tocar

- `app/services/registros_service.py`, `app/api/registros_api.py`
- `app/models/` (si cambia contrato de datos)
- `tests/unit/test_repository.py`

## Skills (links)

- [data_access_layer](../skills/data_access_layer.md)
- [security_privacy](../skills/security_privacy.md)
- [testing_python](../skills/testing_python.md)
- [code_style_python](../skills/code_style_python.md)
- [token_efficiency](../skills/token_efficiency.md)

## Prompts cortos recomendados

```
Datos/API: [operación] en registros_service + registros_api — cliente REST, sin SQL local.
```

```
Contrato: nuevo campo para backend — actualizar payload/parseo y tests de repository con mocks.
```
