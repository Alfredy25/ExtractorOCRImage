# Skill: Testing (pytest)

## Principios

- Framework: **pytest** (`tests/`, p. ej. `tests/unit/`).
- Tests **rápidos**, deterministas; mocks para API externa (OpenAI).
- Tras cambios en core o datos, ejecutar al menos los tests relacionados.

## Checklist

- [ ] ¿Nuevo comportamiento tiene aserción directa?
- [ ] ¿Fixtures locales o `tmp_path` para DB de prueba?
- [ ] `pytest tests/ -v` pasa antes de dar por cerrado.

## Do / Don’t

| Do | Don’t |
|----|--------|
| Nombres `test_*.py`, funciones `test_*` | Depender del orden global de tests |
| Aislar filesystem bajo directorio temporal | Borrar `db.sqlite3` real del usuario |

## Plantillas de prompts cortos

```
Test: cubrir [función] en [módulo] — pytest tests/unit/test_[x].py -v
```

```
Regression: fallo en [caso] — mínimo test que falle antes del fix.
```

## Referencias en el repo

- `tests/unit/test_repository.py`
- `tests/unit/test_parsing.py`
- `tests/unit/test_exporters.py`
- `tests/unit/test_crop_tools.py`
