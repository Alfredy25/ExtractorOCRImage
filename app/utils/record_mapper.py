"""Conversión de datos del formulario al contrato de persistencia."""

from app.models.field_schema import FIELD_KEYS


def to_db_record(form_data: dict, meta: dict) -> dict:
    """Construye un registro alineado con la API y la base local."""
    campos = form_data.get("campos", {})
    record = {
        "sede": meta.get("sede", ""),
        "nombre_imagen": meta.get("nombre_imagen", ""),
        "destinatario_raw": form_data.get("destinatario_raw", "") or "",
        "observaciones_ia": form_data.get("observaciones_ia"),
        "crop_x": meta.get("crop_x"),
        "crop_y": meta.get("crop_y"),
        "crop_w": meta.get("crop_w"),
        "crop_h": meta.get("crop_h"),
        "rotation_deg": meta.get("rotation_deg"),
        "aspect_mode": meta.get("aspect_mode", "FREE"),
    }
    for key in FIELD_KEYS:
        record[key] = campos.get(key, "")
    return record
