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
            "indicaciones": "Entre calles",
            "nombre_o_titulo": "Juan",
            "cargo_dependencia": "",
            "direccion": "",
            "colonia": "",
            "municipio_o_alcaldia": "",
            "estado": "",
            "codigo_postal": "",
            "contacto": "",
            "extras": "",
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
            "indicaciones": "",
            "nombre_o_titulo": "María",
            "cargo_dependencia": "",
            "direccion": "",
            "colonia": "",
            "municipio_o_alcaldia": "",
            "estado": "",
            "codigo_postal": "",
            "contacto": "",
            "extras": "",
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
