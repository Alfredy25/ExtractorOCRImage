"""Tests del repositorio."""
import tempfile
from datetime import date
from pathlib import Path

import pytest

from app.core.repository import (
    create_tables,
    get_connection,
    insert_extraction,
    list_by_date_range,
)
from app.config import DB_PATH


@pytest.fixture
def temp_db(monkeypatch):
    with tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False) as f:
        path = f.name
    monkeypatch.setattr("app.core.repository.DB_PATH", Path(path))
    monkeypatch.setattr("app.core.repository.DATA_DIR", Path(path).parent)
    try:
        yield path
    finally:
        Path(path).unlink(missing_ok=True)


def test_insert_and_list(temp_db):
    conn = get_connection()
    create_tables(conn)

    record = {
        "sede": "AJUSCO",
        "nombre_imagen": "test.jpg",
        "destinatario_raw": "TEXTO",
        "campos_nombre_o_titulo": "Juan",
        "campos_cargo_dependencia": None,
        "campos_direccion": "",
        "campos_colonia": "ILEGIBLE",
        "campos_municipio_o_alcaldia": None,
        "campos_estado": "CDMX",
        "campos_codigo_postal": None,
        "campos_extras": None,
        "campos_contacto": None,
        "campos_indicaciones": None,
        "observaciones_ia": "Sin observaciones",
        "crop_x": 0,
        "crop_y": 0,
        "crop_w": 100,
        "crop_h": 100,
        "rotation_deg": 0,
        "aspect_mode": "FREE",
    }
    rowid = insert_extraction(record)
    assert rowid > 0

    rows = list_by_date_range(date.today(), date.today())
    assert len(rows) >= 1
    r = next(x for x in rows if x["nombre_imagen"] == "TEST.JPG")
    assert r["sede"] == "AJUSCO"
    assert r["campos_colonia"] == "ILEGIBLE"
    assert r["campos_nombre_o_titulo"] == "JUAN"
