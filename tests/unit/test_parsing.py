"""Tests de parsing."""
import pytest

from app.services.parsing_service import _fallback_extraccion, parse_extraccion


def test_parse_valid_json():
    raw = '''
    {
      "destinatario_raw": "TEXTO RAW",
      "campos": {
        "nombre_titulo": "Juan Pérez",
        "cargo_dependencia": "",
        "direccion": "Calle 1",
        "colonia": "Centro",
        "municipio_alcaldia": "",
        "estado": "CDMX",
        "codigo_postal": "06000",
        "numero_volante": "VCS-12-100000-00001",
        "extras": "",
        "contacto": "",
        "indicaciones": "ilegible"
      },
      "observaciones_ia": "Sin observaciones."
    }
    '''
    result = parse_extraccion(raw)
    assert result.destinatario_raw == "TEXTO RAW"
    assert result.campos.nombre_titulo == "Juan Pérez"
    assert result.campos.numero_volante == "VCS-12-100000-00001"
    assert result.campos.indicaciones == "ilegible"
    assert result.observaciones_ia == "Sin observaciones."


def test_parse_invalid_json_fallback():
    result = parse_extraccion("no es json")
    assert result.destinatario_raw == ""
    assert "No se obtuvo JSON válido del modelo." in result.observaciones_ia


def test_fallback_extraccion():
    result = _fallback_extraccion()
    assert result.destinatario_raw == ""
    assert all(
        result.campos.model_dump()[k] == "" for k in result.campos.model_dump()
    )
    assert "No se obtuvo JSON válido del modelo." in result.observaciones_ia
