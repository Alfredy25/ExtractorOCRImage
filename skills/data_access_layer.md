# Skill: Data access layer (DAL API-only)

## Principios

- **Una sola fachada** para persistencia cliente: `app/services/registros_service.py`.
- La UI y el cliente OpenAI **no** acceden a base de datos local ni ejecutan SQL.
- El transporte HTTP y parsing de respuestas viven en `app/api/registros_api.py`.

## Checklist

- [ ] ¿El servicio de registros delega en API (`create_registro`, `list_registros`)?
- [ ] ¿Los payloads/query params están normalizados (fechas ISO, sede, opcionales)?
- [ ] ¿Tests de repositorio actualizados con mocks API?

## Do / Don’t

| Do | Don’t |
|----|--------|
| Funciones de dominio (`insert_extraction`, `list_by_date_range`) | Llamadas HTTP directas desde `main_window.py` |
| Normalizar payloads y errores de sesión en `registros_service` | Acoplar UI a detalles de `httpx` |
| Validar contrato con tests mockeados | Agregar dependencias SQL o scripts de migración al cliente |

## Plantillas de prompts cortos

```
DAL API-only: [operación] en registros_service/registros_api; sin UI; pytest test_repository.
```

```
Nuevo campo de contrato API: actualizar payload/parseo y pruebas con mocks.
```

## Referencias en el repo

- `app/services/registros_service.py`
- `app/api/registros_api.py`
- `tests/unit/test_repository.py`
