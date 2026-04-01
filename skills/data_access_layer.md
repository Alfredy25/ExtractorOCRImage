# Skill: Data access layer (DAL)

## Principios

- **Un solo lugar** para SQL y transacciones: preferentemente `app/core/repository.py` (ajustar si el repo evoluciona).
- La UI y el cliente OpenAI **no** ejecutan SQL.
- Tipos y filas mapeados a modelos/domain claros antes de subir a la UI.

## Checklist

- [ ] ¿Todas las consultas parametrizadas (sin concatenar inputs de usuario)?
- [ ] ¿Transacciones explícitas donde haya varias escrituras?
- [ ] ¿Tests de repositorio actualizados al cambiar esquema?

## Do / Don’t

| Do | Don’t |
|----|--------|
| Funciones con nombres de dominio (`save_*`, `list_*`) | Queries sueltas en `main_window.py` |
| Rutas de DB desde `app/config.py` (`DB_PATH`) | Paths absolutos máquina-local en código |
| Comentario breve si un campo prepara InnoDB futuro | Migración MySQL sin tarea aprobada |

## Plantillas de prompts cortos

```
DAL: [operación] en repository — SQLite; sin UI; pytest test_repository.
```

```
Nueva columna: migración local sqlite + test; nota InnoDB en comentario (ver db_strategy_innodb).
```

## Referencias en el repo

- `app/core/repository.py`
- `app/config.py` — `DB_PATH`, `DATA_DIR`
- `app/data/` — ubicación típica de `db.sqlite3`
- `tests/unit/test_repository.py`
