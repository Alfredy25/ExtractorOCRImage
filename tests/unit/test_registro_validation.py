"""Tests del contrato y la validación acumulativa de registros."""

from app.models.registro import RegistroRequest, validate_registro
from app.services.registros_service import (
    _record_to_insert_payload,
    validate_extraction,
)


def _valid_record() -> dict:
    return {
        "sede": "AJUSCO",
        "nombre_imagen": "IMG_20260204_140120.jpg",
        "destinatario_raw": (
            "C. JOHN DOE PRESIDENTE MUNICIPAL PLAZA DE LA BANDERA CENTRO"
        ),
        "nombre_titulo": "C. John Doe",
        "municipio_alcaldia": "Hola Mundo",
        "codigo_postal": "50000",
        "numero_volante": "VCS-12-100000-00001",
        "crop_x": 0,
        "crop_y": 1,
        "crop_w": 100,
        "crop_h": 50,
        "rotation_deg": 90,
        "aspect_mode": "FREE",
    }


def test_registro_request_serialization_and_deserialization():
    model, errors = validate_registro(_valid_record())

    assert errors == []
    assert isinstance(model, RegistroRequest)
    serialized = model.model_dump(exclude_none=True)
    assert serialized["nombre_titulo"] == "C. John Doe"
    assert serialized["municipio_alcaldia"] == "Hola Mundo"
    assert serialized["numero_volante"] == "VCS-12-100000-00001"


def test_validate_extraction_accumulates_all_errors():
    record = _valid_record()
    record.update({
        "nombre_imagen": "corta.jpg",
        "destinatario_raw": "muy corto",
        "codigo_postal": "123",
        "numero_volante": "VOL-1",
        "crop_x": -1,
        "aspect_mode": "INVALID",
    })

    errors = validate_extraction(record)
    fields = {error["campo"] for error in errors}

    assert {
        "nombre_imagen",
        "destinatario_raw",
        "codigo_postal",
        "numero_volante",
        "crop_x",
        "aspect_mode",
    } <= fields
    assert len(errors) >= 6


def test_payload_omits_empty_optional_fields():
    record = _valid_record()
    record.update({
        "nombre_titulo": "",
        "municipio_alcaldia": None,
        "numero_volante": "   ",
        "crop_x": None,
        "crop_y": None,
    })

    payload = _record_to_insert_payload(record)

    assert "nombre_titulo" not in payload
    assert "municipio_alcaldia" not in payload
    assert "numero_volante" not in payload
    assert "crop_x" not in payload
    assert "crop_y" not in payload


def test_payload_uses_new_property_names():
    payload = _record_to_insert_payload(_valid_record())

    assert payload["nombre_titulo"] == "C. JOHN DOE"
    assert payload["municipio_alcaldia"] == "HOLA MUNDO"
    assert payload["numero_volante"] == "VCS-12-100000-00001"
