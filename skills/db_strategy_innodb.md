# Skill: Estrategia DB — SQLite ahora, InnoDB después

## Principios

- **Hoy**: SQLite es la fuente de verdad en desarrollo y app local (`DB_PATH` en `app/config.py`).
- **Futuro (planeado)**: MySQL **InnoDB**, entorno tipo **CyberPanel**, base **`tools_OCR`**. Esto es **diseño y documentación**; **no** ejecutar migración en este skill.

## Checklist (diseño sin migrar)

- [ ] ¿Tipos de columna elegidos pensando en MySQL (p. ej. evitar tipos raros irreproducibles)?
- [ ] ¿Claves primarias y unicidad definidas como lo haría InnoDB?
- [ ] ¿DAL expone operaciones por dominio, no por SQL dialect‑specific en la UI?

## Do / Don’t

| Do | Don’t |
|----|--------|
| Documentar en código/DAL el mapeo futuro | Conectar `tools_OCR` en código productivo sin decisión explícita |
| Usar transacciones y constraints compatibles con ambos motores | Depender de features solo SQLite sin aislar |
| Variables de entorno para credenciales MySQL **cuando** exista tarea | Commitear `.env` con passwords |

## Plantillas de prompts cortos

```
DB futuro: revisar [tabla/columna] para compatibilidad InnoDB — solo análisis y DAL; sin deploy.
```

```
Preparar interfaz Repository para backend swap — SQLite impl actual intacta.
```

## Referencias en el repo

- `app/config.py` — `DB_PATH`, `DATA_DIR`
- `app/core/repository.py`
- `agents/data_db.agent.md` — límites del subagente

## Nota

Cuando exista la tarea de migración: nuevo conector, pruebas de integración y plan de datos; hasta entonces **SQLite only** en ejecución.
