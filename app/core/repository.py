"""Repositorio de extracciones: SQLite (desarrollo) o MySQL InnoDB (producción)."""
from __future__ import annotations

import contextlib
import sqlite3
from datetime import date
from pathlib import Path
from typing import Iterator

import app.config as app_config
from app.config import DB_PATH, DATA_DIR

# Raíz del proyecto (…/ExtractorOcrImagenes)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Migración SQLite: renombrar columnas antiguas campos_*.
_LEGACY_CAMPOS_TO_COLUMN = [
    ("campos_nombre_o_titulo", "nombre_o_titulo"),
    ("campos_cargo_dependencia", "cargo_dependencia"),
    ("campos_direccion", "direccion"),
    ("campos_colonia", "colonia"),
    ("campos_municipio_o_alcaldia", "municipio_o_alcaldia"),
    ("campos_estado", "estado"),
    ("campos_codigo_postal", "codigo_postal"),
    ("campos_extras", "extras"),
    ("campos_contacto", "contacto"),
    ("campos_indicaciones", "indicaciones"),
]


def _ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _field_to_db(value: str | None, is_destinatario_raw: bool = False) -> str | None:
    """
    Mapeo UI -> BD:
    - Vacío -> NULL (excepto destinatario_raw que puede ser "")
    - "ILEGIBLE" (case-insensitive) -> "ILEGIBLE"
    - Otro texto -> MAYÚSCULAS
    """
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None if not is_destinatario_raw else ""
    if "ilegible" in s.lower():
        return "ILEGIBLE"
    return s.upper()


def _placeholder(engine: str) -> str:
    return "%s" if engine == "mysql" else "?"


def create_tables_sqlite(conn: sqlite3.Connection) -> None:
    """Crea las tablas en SQLite."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS extractions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sede TEXT NOT NULL CHECK (sede IN ('AJUSCO', 'COYOACÁN')),
            nombre_imagen TEXT NOT NULL,
            destinatario_raw TEXT NOT NULL,
            nombre_o_titulo TEXT,
            cargo_dependencia TEXT,
            direccion TEXT,
            colonia TEXT,
            municipio_o_alcaldia TEXT,
            estado TEXT,
            codigo_postal TEXT,
            extras TEXT,
            contacto TEXT,
            indicaciones TEXT,
            observaciones_ia TEXT,
            crop_x INTEGER,
            crop_y INTEGER,
            crop_w INTEGER,
            crop_h INTEGER,
            rotation_deg INTEGER,
            aspect_mode TEXT CHECK (aspect_mode IN ('FREE', 'SQUARE')),
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_extractions_created_at ON extractions(created_at)"
    )
    conn.commit()


def migrate_extractions_legacy_columns_sqlite(conn: sqlite3.Connection) -> None:
    """Renombra columnas campos_* en SQLite existente (SQLite 3.25+)."""
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='extractions'"
    )
    if not cur.fetchone():
        return
    cur = conn.execute("PRAGMA table_info(extractions)")
    cols = {row[1] for row in cur.fetchall()}
    for old, new in _LEGACY_CAMPOS_TO_COLUMN:
        if old in cols and new not in cols:
            conn.execute(f'ALTER TABLE extractions RENAME COLUMN "{old}" TO "{new}"')
            cols.remove(old)
            cols.add(new)
    conn.commit()


def _mysql_schema_statements() -> list[str]:
    path = _PROJECT_ROOT / "sql" / "schema_mysql.sql"
    raw = path.read_text(encoding="utf-8")
    stmts: list[str] = []
    for chunk in raw.split(";"):
        lines = []
        for line in chunk.splitlines():
            line = line.strip()
            if not line or line.startswith("--"):
                continue
            lines.append(line)
        s = " ".join(lines).strip()
        if s:
            stmts.append(s + ";")
    return stmts


def ensure_mysql_tables(conn) -> None:
    """Ejecuta sql/schema_mysql.sql (CREATE IF NOT EXISTS)."""
    cur = conn.cursor()
    for stmt in _mysql_schema_statements():
        cur.execute(stmt)
    conn.commit()
    cur.close()


@contextlib.contextmanager
def get_connection() -> Iterator[tuple[object, str]]:
    """
    Context manager: (connection, engine) donde engine es ``sqlite`` o ``mysql``.
    Cierra la conexión al salir.
    """
    if app_config.is_mysql():
        import pymysql

        cfg = app_config.get_mysql_config()
        if not cfg.get("user"):
            raise RuntimeError(
                "DB_ENGINE=mysql requiere DB_USER (y demás variables). Ver .env.example."
            )
        conn = pymysql.connect(
            host=cfg["host"],
            port=cfg["port"],
            user=cfg["user"],
            password=cfg["password"],
            database=cfg["database"],
            charset=cfg["charset"],
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False,
        )
        try:
            ensure_mysql_tables(conn)
            yield conn, "mysql"
        finally:
            conn.close()
        return

    _ensure_data_dir()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    create_tables_sqlite(conn)
    migrate_extractions_legacy_columns_sqlite(conn)
    try:
        yield conn, "sqlite"
    finally:
        conn.close()


def insert_extraction(record: dict) -> int:
    """Inserta un registro y devuelve el id."""
    params = (
        _field_to_db(record.get("sede"), False) or record.get("sede", "").upper(),
        _field_to_db(record.get("nombre_imagen"), False)
        or record.get("nombre_imagen", "").upper(),
        _field_to_db(record.get("destinatario_raw"), True) or "",
        _field_to_db(record.get("nombre_o_titulo")),
        _field_to_db(record.get("cargo_dependencia")),
        _field_to_db(record.get("direccion")),
        _field_to_db(record.get("colonia")),
        _field_to_db(record.get("municipio_o_alcaldia")),
        _field_to_db(record.get("estado")),
        _field_to_db(record.get("codigo_postal")),
        _field_to_db(record.get("extras")),
        _field_to_db(record.get("contacto")),
        _field_to_db(record.get("indicaciones")),
        _field_to_db(record.get("observaciones_ia")),
        record.get("crop_x"),
        record.get("crop_y"),
        record.get("crop_w"),
        record.get("crop_h"),
        record.get("rotation_deg"),
        record.get("aspect_mode", "FREE"),
    )

    with get_connection() as (conn, engine):
        ph = _placeholder(engine)
        sql = f"""
            INSERT INTO extractions (
                sede, nombre_imagen, destinatario_raw,
                nombre_o_titulo, cargo_dependencia, direccion,
                colonia, municipio_o_alcaldia, estado,
                codigo_postal, extras, contacto, indicaciones,
                observaciones_ia, crop_x, crop_y, crop_w, crop_h, rotation_deg, aspect_mode
            ) VALUES ({",".join([ph] * 20)})
            """
        if engine == "mysql":
            cur = conn.cursor()
            cur.execute(sql, params)
            conn.commit()
            last = cur.lastrowid
            cur.close()
            return int(last)
        cur = conn.execute(sql, params)
        conn.commit()
        return int(cur.lastrowid)


def list_by_date_range(desde: date, hasta: date) -> list[dict]:
    """Lista registros por rango de fechas (incluyente)."""
    with get_connection() as (conn, engine):
        ph = _placeholder(engine)
        if engine == "mysql":
            sql = f"""
            SELECT * FROM extractions
            WHERE DATE(created_at) >= DATE({ph}) AND DATE(created_at) <= DATE({ph})
            ORDER BY created_at
            """
        else:
            sql = f"""
            SELECT * FROM extractions
            WHERE date(created_at) >= date({ph}) AND date(created_at) <= date({ph})
            ORDER BY created_at
            """
        if engine == "mysql":
            cur = conn.cursor()
            cur.execute(sql, (desde.isoformat(), hasta.isoformat()))
            rows = cur.fetchall()
            cur.close()
            return [dict(r) for r in rows]
        cur = conn.execute(sql, (desde.isoformat(), hasta.isoformat()))
        rows = cur.fetchall()
        return [dict(row) for row in rows]
