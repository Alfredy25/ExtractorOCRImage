# Subagente: Datos / DB

## Propósito

**Capa de acceso a datos** y coherencia del esquema en **SQLite** (actual). Preparar **compatibilidad conceptual** con **MySQL InnoDB** (`tools_OCR` en CyberPanel) **sin ejecutar migración** hasta decisión explícita.

## Cuándo usarlo

- Cambios en `app/core/repository.py`, rutas en `app/config.py` relacionadas con `DB_PATH` / `DATA_DIR`.
- Nuevas tablas, índices, migraciones locales SQLite **cuando el alcance lo exija**.
- Tests en `tests/unit/test_repository.py`.

## Cuándo NO

- Rediseño de widgets → **ui_pyside6**.
- Algoritmos de OCR/parsing sin tocar persistencia → **core_backend**.
- Solo cablear botones → **fullstack_integration**.

## Decisiones que SÍ puede tomar

- Consultas y transacciones en SQLite dentro del repositorio/DAL.
- Refactor para centralizar SQL en un solo módulo/capa.
- Documentar mapeo futuro columnas tipos SQLite ↔ MySQL en comentarios o skill (no despliegue).

## Decisiones que NO puede tomar

- **No** conectar producción a MySQL ni ejecutar scripts en servidor CyberPanel en esta base de trabajo.
- **No** cambiar el motor por defecto de la app sin tarea de migración aprobada.
- **No** exponer credenciales de BD en código o `.env` versionado.

## Checklist de trabajo

- [ ] ¿Todo SQL vive en la capa de datos (p. ej. `repository.py`), no en UI?
- [ ] ¿Tests de repositorio actualizados?
- [ ] Skills: [`skills/data_access_layer.md`](../skills/data_access_layer.md), [`skills/db_strategy_innodb.md`](../skills/db_strategy_innodb.md), [`skills/security_privacy.md`](../skills/security_privacy.md), [`skills/testing_python.md`](../skills/testing_python.md)
- [ ] `pytest tests/unit/test_repository.py -v`

## Archivos que suele tocar

- `app/core/repository.py`, `app/core/models.py` (si afecta persistencia)
- `app/config.py` (`DB_PATH`, `DATA_DIR`)
- `app/data/` (ubicación de sqlite; no commitear datos sensibles)
- `tests/unit/test_repository.py`

## Skills (links)

- [data_access_layer](../skills/data_access_layer.md)
- [db_strategy_innodb](../skills/db_strategy_innodb.md)
- [security_privacy](../skills/security_privacy.md)
- [testing_python](../skills/testing_python.md)
- [code_style_python](../skills/code_style_python.md)
- [token_efficiency](../skills/token_efficiency.md)

## Prompts cortos recomendados

```
Datos: [operación] en repository — SQLite only; sin migración MySQL; alinear con db_strategy_innodb.
```

```
Esquema: nueva columna/tab local — tests repository; documentar nota InnoDB futura en DAL comment.
```
