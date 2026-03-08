"""Tests de exporters."""
import tempfile
from pathlib import Path

import pytest

from app.core.exporters import export_csv, export_excel, suggested_filename


def test_export_csv():
    records = [
        {
            "created_at": "2025-03-07 12:00:00",
            "nombre_imagen": "test.jpg",
            "destinatario_raw": "TEXTO",
            "campos_indicaciones": "Entre calles",
            "campos_nombre_o_titulo": "Juan",
            "campos_cargo_dependencia": "",
            "campos_direccion": "",
            "campos_colonia": "",
            "campos_municipio_o_alcaldia": "",
            "campos_estado": "",
            "campos_codigo_postal": "",
            "campos_contacto": "",
            "campos_extras": "",
            "observaciones_ia": "",
        }
    ]
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
        path = Path(f.name)
    try:
        export_csv(records, path)
        content = path.read_text(encoding="utf-8-sig")
        assert "fecha" in content
        assert "Juan" in content
        assert "Entre calles" in content
    finally:
        path.unlink(missing_ok=True)


def test_export_excel():
    records = [
        {
            "created_at": "2025-03-07 12:00:00",
            "nombre_imagen": "test.jpg",
            "destinatario_raw": "TEXTO",
            "campos_indicaciones": "",
            "campos_nombre_o_titulo": "María",
            "campos_cargo_dependencia": "",
            "campos_direccion": "",
            "campos_colonia": "",
            "campos_municipio_o_alcaldia": "",
            "campos_estado": "",
            "campos_codigo_postal": "",
            "campos_contacto": "",
            "campos_extras": "",
            "observaciones_ia": "",
        }
    ]
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        path = Path(f.name)
    try:
        export_excel(records, path)
        assert path.exists()
    finally:
        path.unlink(missing_ok=True)


def test_suggested_filename():
    name = suggested_filename("xlsx")
    assert name.endswith(".xlsx")
    assert "procesados" in name
