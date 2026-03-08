"""Repositorio SQLite para extracciones."""
import sqlite3
from datetime import date, datetime
from pathlib import Path

from app.config import DB_PATH, DATA_DIR


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
            campos_nombre_o_titulo TEXT,
            campos_cargo_dependencia TEXT,
            campos_direccion TEXT,
            campos_colonia TEXT,
            campos_municipio_o_alcaldia TEXT,
            campos_estado TEXT,
            campos_codigo_postal TEXT,
            campos_extras TEXT,
            campos_contacto TEXT,
            campos_indicaciones TEXT,
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


def get_connection() -> sqlite3.Connection:
    """Obtiene una conexión a la BD y crea tablas si no existen."""
    _ensure_data_dir()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    create_tables(conn)
    return conn


def insert_extraction(record: dict) -> int:
    """Inserta un registro y devuelve el id."""
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO extractions (
                sede, nombre_imagen, destinatario_raw,
                campos_nombre_o_titulo, campos_cargo_dependencia, campos_direccion,
                campos_colonia, campos_municipio_o_alcaldia, campos_estado,
                campos_codigo_postal, campos_extras, campos_contacto, campos_indicaciones,
                observaciones_ia, crop_x, crop_y, crop_w, crop_h, rotation_deg, aspect_mode
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _field_to_db(record.get("sede"), False) or record.get("sede", "").upper(),
                _field_to_db(record.get("nombre_imagen"), False) or record.get("nombre_imagen", "").upper(),
                _field_to_db(record.get("destinatario_raw"), True) or "",
                _field_to_db(record.get("campos_nombre_o_titulo")),
                _field_to_db(record.get("campos_cargo_dependencia")),
                _field_to_db(record.get("campos_direccion")),
                _field_to_db(record.get("campos_colonia")),
                _field_to_db(record.get("campos_municipio_o_alcaldia")),
                _field_to_db(record.get("campos_estado")),
                _field_to_db(record.get("campos_codigo_postal")),
                _field_to_db(record.get("campos_extras")),
                _field_to_db(record.get("campos_contacto")),
                _field_to_db(record.get("campos_indicaciones")),
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
