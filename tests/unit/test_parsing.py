"""Tests de parsing."""
import pytest

from app.core.parsing import parse_extraccion, _fallback_extraccion


def test_parse_valid_json():
    raw = '''
    {
      "destinatario_raw": "TEXTO RAW",
      "campos": {
        "nombre_o_titulo": "Juan Pérez",
        "cargo_dependencia": "",
        "direccion": "Calle 1",
        "colonia": "Centro",
        "municipio_o_alcaldia": "",
        "estado": "CDMX",
        "codigo_postal": "06000",
        "extras": "",
        "contacto": "",
        "indicaciones": "ilegible"
      },
      "observaciones_ia": "Sin observaciones."
    }
    '''
    result = parse_extraccion(raw)
    assert result.destinatario_raw == "TEXTO RAW"
    assert result.campos.nombre_o_titulo == "Juan Pérez"
    assert result.campos.indicaciones == "ilegible"
    assert result.observaciones_ia == "Sin observaciones."


def test_parse_invalid_json_fallback():
    result = parse_extraccion("no es json")
    assert result.destinatario_raw == ""
    assert "No se obtuvo" in result.observaciones_ia


def test_fallback_extraccion():
    result = _fallback_extraccion()
    assert result.destinatario_raw == ""
    assert all(
        result.campos.model_dump()[k] == "" for k in result.campos.model_dump()
    )
    assert "No se obtuvo" in result.observaciones_ia
