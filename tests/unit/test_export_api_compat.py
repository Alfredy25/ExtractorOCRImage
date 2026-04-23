# [NUEVO] Fase 8: contrato GET /registros → filas de exportación (sin backend generando archivos).

"""Validación de forma de respuesta API frente a normalización y exportación local."""

from datetime import date, datetime
from pathlib import Path
import tempfile

import pandas as pd
import pytest

from app.core.exporters import (
    EXPORT_COLUMNS,
    _records_to_rows,
    export_excel,
    normalize_registro_for_export,
    normalize_registros_for_export,
)


def _sample_api_registro() -> dict:
    """Ejemplo alineado con el contrato compartido (campos extra id/auditoría permitidos)."""
    return {
        "sede": "AJUSCO",
        "nombre_imagen": "IMG_20260204_140120.jpg",
        "destinatario_raw": "C.P. BLANCA GUADALUPE ORTA IZAGUIRRE SUBSECRETARIA",
        "nombre_o_titulo": "C.P. BLANCA GUADALUPE ORTA IZAGUIRRE",
        "cargo_dependencia": "SUBSECRETARIA DE AUDITORÍA GUBERNAMENTAL",
        "direccion": "Av. Insurgentes Sur 123",
        "colonia": "Del Valle",
        "municipio_o_alcaldia": "SALTILLO",
        "estado": "COAHUILA DE ZARAGOZA",
        "codigo_postal": "03100",
        "extras": None,
        "contacto": "TEL. 844-986-9826",
        "indicaciones": "",
        "observaciones_ia": "Corrección hecha por operador",
        "crop_x": 0,
        "crop_y": 0,
        "crop_w": 0,
        "crop_h": 0,
        "rotation_deg": 0,
        "aspect_mode": "FREE",
        "id": 2,
        "created_at": "2026-04-22T17:35:47",
        "updated_at": "2026-04-22T17:56:30",
        "created_by": 1,
        "updated_by": 1,
    }


def test_normalize_registro_fills_missing_keys():
    minimal = {"created_at": "2026-01-15T00:00:00", "nombre_imagen": "a.jpg"}
    out = normalize_registro_for_export(minimal)
    assert out["destinatario_raw"] is None
    assert out["indicaciones"] is None
    assert out["nombre_imagen"] == "a.jpg"


def test_records_to_rows_api_contract_shape():
    raw = [_sample_api_registro()]
    rows = _records_to_rows(normalize_registros_for_export(raw))
    assert len(rows) == 1
    r = rows[0]
    assert r["fecha"] == "22-04-2026"
    assert r["imagen"] == "IMG_20260204_140120.jpg"
    assert r["extras"] == ""
    assert r["indicaciones"] == ""
    assert r["nombre_o_titulo"] == "C.P. BLANCA GUADALUPE ORTA IZAGUIRRE"
    for col in EXPORT_COLUMNS:
        assert col in r


@pytest.mark.parametrize(
    "created,expected_day",
    [
        ("2026-04-22T17:35:47", "22-04-2026"),
        ("2026-04-22 17:35:47", "22-04-2026"),
        (datetime(2026, 4, 22, 17, 35, 47), "22-04-2026"),
        (date(2026, 4, 22), "22-04-2026"),
    ],
)
def test_fecha_from_created_at_variants(created, expected_day):
    rows = _records_to_rows(
        normalize_registros_for_export(
            [{"created_at": created, "nombre_imagen": "x.jpg", "destinatario_raw": "d"}]
        )
    )
    assert rows[0]["fecha"] == expected_day


def test_export_excel_from_api_shape_roundtrip():
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        path = Path(f.name)
    try:
        export_excel([_sample_api_registro()], path)
        df = pd.read_excel(path, engine="openpyxl")
        assert list(df.columns) == EXPORT_COLUMNS
        assert df.iloc[0]["imagen"] == "IMG_20260204_140120.jpg"
        assert df.iloc[0]["fecha"] == "22-04-2026"
    finally:
        path.unlink(missing_ok=True)
