"""Repositorio SQLite para extracciones."""
import sqlite3
from datetime import date
from pathlib import Path

from app.config import DB_PATH, DATA_DIR

# Migración: renombrar columnas antiguas campos_* en SQLite.
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


def create_tables(conn: sqlite3.Connection):
    """Crea las tablas de la BD."""
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


def migrate_extractions_legacy_columns(conn: sqlite3.Connection) -> None:
    """
    Renombra columnas campos_* a nombres sin prefijo en BD existentes (SQLite 3.25+).
    """
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


def get_connection() -> sqlite3.Connection:
    """Obtiene una conexión a la BD y crea tablas si no existen."""
    _ensure_data_dir()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    create_tables(conn)
    migrate_extractions_legacy_columns(conn)
    return conn


def insert_extraction(record: dict) -> int:
    """Inserta un registro y devuelve el id."""
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO extractions (
                sede, nombre_imagen, destinatario_raw,
                nombre_o_titulo, cargo_dependencia, direccion,
                colonia, municipio_o_alcaldia, estado,
                codigo_postal, extras, contacto, indicaciones,
                observaciones_ia, crop_x, crop_y, crop_w, crop_h, rotation_deg, aspect_mode
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
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
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def list_by_date_range(desde: date, hasta: date) -> list[dict]:
    """Lista registros por rango de fechas (incluyente)."""
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            SELECT * FROM extractions
            WHERE date(created_at) >= date(?) AND date(created_at) <= date(?)
            ORDER BY created_at
            """,
            (desde.isoformat(), hasta.isoformat()),
        )
        rows = cur.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
