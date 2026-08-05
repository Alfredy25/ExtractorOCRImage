"""Tests del mapeo entre formulario y contrato de registros."""

from app.utils.record_mapper import to_db_record


def test_to_db_record_maps_new_field_names():
    form_data = {
        "destinatario_raw": "Texto bruto",
        "campos": {
            "nombre_titulo": "C. Juan Pérez",
            "municipio_alcaldia": "Coyoacán",
            "numero_volante": "VCS-12-100000-00001",
        },
        "observaciones_ia": "Sin observaciones.",
    }
    meta = {
        "sede": "AJUSCO",
        "nombre_imagen": "IMG_20260204_140120.jpg",
        "crop_x": 1,
        "crop_y": 2,
        "crop_w": 3,
        "crop_h": 4,
        "rotation_deg": 0,
        "aspect_mode": "FREE",
    }

    record = to_db_record(form_data, meta)

    assert record["nombre_titulo"] == "C. Juan Pérez"
    assert record["municipio_alcaldia"] == "Coyoacán"
    assert record["numero_volante"] == "VCS-12-100000-00001"
