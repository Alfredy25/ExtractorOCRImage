"""Tests del repositorio."""
import tempfile
from datetime import date, datetime, time
from pathlib import Path

import pytest

from app.core.repository import insert_extraction, list_by_date_range


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
    record = {
        "sede": "AJUSCO",
        "nombre_imagen": "test.jpg",
        "destinatario_raw": "TEXTO",
        "nombre_o_titulo": "Juan",
        "cargo_dependencia": None,
        "direccion": "",
        "colonia": "ILEGIBLE",
        "municipio_o_alcaldia": None,
        "estado": "CDMX",
        "codigo_postal": None,
        "extras": None,
        "contacto": None,
        "indicaciones": None,
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

    day = date.today()
    start = datetime.combine(day, time.min)
    end = datetime.combine(day, time(23, 59, 59))
    rows = list_by_date_range(start, end)
    assert len(rows) >= 1
    r = next(x for x in rows if x["nombre_imagen"] == "TEST.JPG")
    rows_ajusco = list_by_date_range(start, end, "AJUSCO")
    assert any(x["nombre_imagen"] == "TEST.JPG" for x in rows_ajusco)
    assert r["sede"] == "AJUSCO"
    assert r["colonia"] == "ILEGIBLE"
    assert r["nombre_o_titulo"] == "JUAN"
