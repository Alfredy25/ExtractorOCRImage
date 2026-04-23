# Migración SQLite → MySQL (InnoDB, `tools_OCR`)

Documentación para CyberPanel / MySQL 8+ o MariaDB 10.3+ con `utf8mb4`.

## FASE 1 — Análisis (resumen)

| Elemento | Detalle |
|----------|---------|
| **Acceso** | Capa propia: `app/core/repository.py` (antes solo `sqlite3`). |
| **Conexión SQLite** | `app/config.py` → `DB_PATH` (`app/data/db.sqlite3`). |
| **Conexión MySQL** | Variables `DB_*` en `.env`; cliente **PyMySQL**. |
| **Tabla** | `extractions` — un registro por extracción/guardado desde la UI. |
| **Columnas** | `id`, `sede`, `nombre_imagen`, `destinatario_raw`, campos de destinatario (`nombre_o_titulo`, …), `observaciones_ia`, recorte (`crop_*`, `rotation_deg`, `aspect_mode`), `created_at`, `updated_at`. |
| **Índice** | `idx_extractions_created_at` sobre `created_at` (exportes por rango de fechas). |

No hay FKs a otras tablas en la app actual.

---

## FASE 2 — Configuración `.env`

Copia de referencia en `.env.example`. Para MySQL:

```env
DB_ENGINE=mysql
DB_HOST=tu-servidor
DB_PORT=3306
DB_USER=tu_usuario
DB_PASSWORD=tu_contraseña
DB_NAME=tools_OCR
```

- Crea la base `tools_OCR` en CyberPanel **antes** de conectar.
- **No** subas `.env` al repositorio.

Desarrollo local sin MySQL: omite `DB_ENGINE` o usa `DB_ENGINE=sqlite`.

---

## FASE 3 — Esquema InnoDB

- **Archivo SQL:** `sql/schema_mysql.sql` (fuente de verdad).
- **Aplicar manualmente:**  
  `mysql -h HOST -u USER -p tools_OCR < sql/schema_mysql.sql`
- **O con Python:**  
  `python scripts/create_mysql_schema.py`  
  (usa las mismas variables `.env` que la app para MySQL).

La app también ejecuta el mismo DDL al conectar (si falta la tabla), pero conviene aplicar el esquema una vez en el servidor de forma controlada.

---

## FASE 4 — Migración de datos

1. Asegúrate de que SQLite tiene el esquema **actual** (columnas sin prefijo `campos_*`). Si hace falta, abre la app una vez con SQLite para que corra la migración de columnas.
2. Crea esquema en MySQL (paso anterior).
3. Ejecuta desde la **raíz del proyecto**:

```bash
python scripts/migrate_sqlite_to_mysql.py --dry-run
python scripts/migrate_sqlite_to_mysql.py
```

Opcional: `--sqlite-path RUTA\db.sqlite3` si el archivo no está en `app/data/db.sqlite3`.

- Conserva `id` originales.
- Si un `id` ya existe en MySQL, la fila se **omite** (duplicado).
- Al final ajusta `AUTO_INCREMENT`.

---

## FASE 5 — Verificación

```bash
python scripts/check_db.py
```

Comprueba `SELECT 1` y `SELECT COUNT(*) FROM extractions`.

Al arrancar la app (`python -m app.main`), en log aparece una línea del tipo:  
`Base de datos: MySQL host:3306/tools_OCR` (sin contraseña).

---

## ✅ Qué hacer después de migrar

1. **Confirmar que la app usa MySQL**  
   - Revisa `logs/extractor_ocr.log` (línea de arranque con resumen de BD).  
   - En `.env`: `DB_ENGINE=mysql` y credenciales correctas.

2. **Eliminar o desactivar dependencias de SQLite en producción**  
   - No hace falta borrar `db.sqlite3` de inmediato; guárdalo como backup hasta validar.  
   - No dejes rutas fijas a SQLite en código nuevo (usa siempre `repository` / `config`).

3. **Validar funcionalidad**  
   - Inserción: guardar un registro desde la UI.  
   - Lectura: exportar por rango de fechas.  
   - Exportación: CSV/Excel con datos coherentes.

4. **Tests**  

   ```bash
   pytest tests/ -v
   ```  

   Los tests fuerzan `DB_ENGINE=sqlite` (`tests/conftest.py`) y no necesitan MySQL.

5. **Backup inicial de MySQL**  
   - En CyberPanel / `mysqldump`: respaldo de `tools_OCR` tras la primera validación.

6. **Reejecutar migración**  
   - El script es idempotente en la medida en que los `id` duplicados se omiten.  
   - Para “empezar de cero” en MySQL: truncar o recrear `extractions` y volver a lanzar el script.

7. **Rollback manual**  
   - Vuelve a `DB_ENGINE=sqlite` en `.env` y restaura `app/data/db.sqlite3` desde backup si lo borraste.  
   - Los datos ya en MySQL no se borran solos; conserva dumps si necesitas volver atrás con datos.

8. **Recomendaciones**  
   - **Índices:** según consultas futuras (p. ej. por `sede` o `nombre_imagen`).  
   - **Conexiones:** cada operación abre y cierra conexión (app de escritorio, tráfico bajo). Si crece el uso, valorar pool.  
   - **Firewall / puerto 3306:** abre solo hacia IPs confiables; en muchos entornos MySQL no está expuesto a Internet sin túnel/VPN.

---

## Troubleshooting

| Problema | Qué revisar |
|----------|-------------|
| `Can't connect to MySQL` | `DB_HOST`, `DB_PORT`, firewall CyberPanel, bind-address del servidor MySQL. |
| `Access denied` | Usuario/contraseña, host permitido (`user@'%'` vs `user@'localhost'`). |
| `Unknown database 'tools_OCR'` | Crear la BD en el panel antes de conectar. |
| `DB_ENGINE=mysql requiere DB_USER` | Variables incompletas en `.env`. |
| Errores de charset | Tabla debe ser `utf8mb4`; el cliente usa `charset=utf8mb4`. |

---

## Checklist final (desarrollador)

- [ ] `.env` con `DB_ENGINE=mysql` y `DB_*` completos (sin commitear).  
- [ ] `pip install -r requirements.txt` (incluye PyMySQL).  
- [ ] Esquema aplicado (`schema_mysql.sql` o `create_mysql_schema.py`).  
- [ ] Datos migrados (`migrate_sqlite_to_mysql.py`) si aplica.  
- [ ] `python scripts/check_db.py` → OK.  
- [ ] App arranca y guarda/exporta correctamente.  
- [ ] `pytest tests/ -v` pasa.  
- [ ] Backup MySQL documentado / programado.
