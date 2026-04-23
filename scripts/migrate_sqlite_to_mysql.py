#!/usr/bin/env python3
"""
Copia filas de SQLite (tabla extractions) hacia MySQL (misma estructura).

Uso (raíz del proyecto):
  python scripts/migrate_sqlite_to_mysql.py [--sqlite-path RUTA]

Variables .env para MySQL: DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
No modifica DB_ENGINE; conecta a ambos motores de forma explícita.

Opciones:
  --dry-run   Solo cuenta filas en SQLite, no escribe en MySQL.
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

# Columnas en orden (sin id; id se inserta explícito para conservar PK)
_ROW_COLUMNS = (
    "id",
    "sede",
    "nombre_imagen",
    "destinatario_raw",
    "nombre_o_titulo",
    "cargo_dependencia",
    "direccion",
    "colonia",
    "municipio_o_alcaldia",
    "estado",
    "codigo_postal",
    "extras",
    "contacto",
    "indicaciones",
    "observaciones_ia",
    "crop_x",
    "crop_y",
    "crop_w",
    "crop_h",
    "rotation_deg",
    "aspect_mode",
    "created_at",
    "updated_at",
)


def _sqlite_columns(conn: sqlite3.Connection) -> set[str]:
    cur = conn.execute("PRAGMA table_info(extractions)")
    return {row[1] for row in cur.fetchall()}


def main() -> int:
    import pymysql

    from app.config import DB_PATH, get_mysql_config

    parser = argparse.ArgumentParser(description="Migrar extractions SQLite → MySQL")
    parser.add_argument(
        "--sqlite-path",
        type=Path,
        default=DB_PATH,
        help=f"Ruta al .sqlite3 (por defecto: {DB_PATH})",
    )
    parser.add_argument("--dry-run", action="store_true", help="No insertar en MySQL")
    args = parser.parse_args()

    sqlite_path: Path = args.sqlite_path
    if not sqlite_path.is_file():
        print(f"Error: no existe SQLite: {sqlite_path}", file=sys.stderr)
        return 1

    cfg = get_mysql_config()
    if not cfg.get("user"):
        print("Error: defina DB_USER y credenciales MySQL en .env", file=sys.stderr)
        return 1

    sl = sqlite3.connect(str(sqlite_path))
    sl.row_factory = sqlite3.Row
    cols = _sqlite_columns(sl)
    required = set(_ROW_COLUMNS) - {"updated_at"}
    if not required.issubset(cols):
        missing = required - cols
        print(
            "Error: esquema SQLite incompatible (¿columnas campos_* sin migrar?). "
            f"Faltan: {missing}",
            file=sys.stderr,
        )
        sl.close()
        return 1

    cur_sl = sl.execute("SELECT * FROM extractions ORDER BY id")
    rows = cur_sl.fetchall()
    sl.close()
    print(f"SQLite: {len(rows)} filas leídas.")

    if args.dry_run:
        print("Dry-run: no se escribió en MySQL.")
        return 0

    my = pymysql.connect(
        host=cfg["host"],
        port=cfg["port"],
        user=cfg["user"],
        password=cfg["password"],
        database=cfg["database"],
        charset=cfg["charset"],
        autocommit=False,
    )
    placeholders = ",".join(["%s"] * len(_ROW_COLUMNS))
    sql = f"INSERT INTO extractions ({','.join(_ROW_COLUMNS)}) VALUES ({placeholders})"
    inserted = 0
    skipped = 0
    errors = 0
    from pymysql.err import IntegrityError

    try:
        mc = my.cursor()
        for row in rows:
            d = dict(row)
            values = tuple(d.get(c) for c in _ROW_COLUMNS)
            try:
                mc.execute(sql, values)
                inserted += 1
            except IntegrityError:
                skipped += 1
            except Exception as e:
                print(f"Aviso fila id={d.get('id')}: {e}", file=sys.stderr)
                errors += 1
        my.commit()
        mc.close()

        mc = my.cursor()
        mc.execute("SELECT COALESCE(MAX(id), 0) + 1 AS n FROM extractions")
        next_ai = mc.fetchone()[0]
        mc.execute(f"ALTER TABLE extractions AUTO_INCREMENT = {int(next_ai)}")
        my.commit()
        mc.close()

        print(f"MySQL: insertadas={inserted}, omitidas (duplicado)={skipped}, errores={errors}")
        return 0 if errors == 0 else 2
    except Exception as e:
        my.rollback()
        print(f"Error: {e}", file=sys.stderr)
        return 1
    finally:
        my.close()


if __name__ == "__main__":
    raise SystemExit(main())
