"""Contrato y validación de creación de registros."""
from __future__ import annotations

from typing import Any, Literal, Optional, TypedDict

from pydantic import BaseModel, Field, ValidationError


class RegistroRequest(BaseModel):
    """Cuerpo oficial de ``POST /registros``."""

    sede: Literal["AJUSCO", "COYOACAN"]

    nombre_imagen: str = Field(..., min_length=20, max_length=50)
    destinatario_raw: str = Field(..., min_length=40, max_length=660)

    nombre_titulo: Optional[str] = Field(default=None, max_length=200)
    cargo_dependencia: Optional[str] = Field(default=None, max_length=255)
    direccion: Optional[str] = Field(default=None, max_length=255)
    colonia: Optional[str] = Field(default=None, max_length=150)
    municipio_alcaldia: Optional[str] = Field(default=None, max_length=100)
    estado: Optional[str] = Field(default=None, max_length=100)
    codigo_postal: Optional[str] = Field(default=None, min_length=4, max_length=6)

    numero_volante: Optional[str] = Field(default=None, min_length=15, max_length=25)
    extras: Optional[str] = Field(default=None, max_length=420)
    contacto: Optional[str] = Field(default=None, max_length=150)
    indicaciones: Optional[str] = Field(default=None, max_length=200)
    observaciones_ia: Optional[str] = Field(default=None, max_length=100)

    crop_x: Optional[int] = Field(default=0, ge=0)
    crop_y: Optional[int] = Field(default=0, ge=0)
    crop_w: Optional[int] = Field(default=0, ge=0)
    crop_h: Optional[int] = Field(default=0, ge=0)
    rotation_deg: Optional[int] = Field(default=0, ge=0)

    aspect_mode: Literal["FREE", "SQUARE"]


class RegistroFieldError(TypedDict):
    """Error de validación presentable al usuario."""

    campo: str
    error: str


_LENGTH_MESSAGES = {
    "nombre_imagen": "Debe tener entre 20 y 50 caracteres",
    "destinatario_raw": "Debe tener entre 40 y 660 caracteres",
    "nombre_titulo": "Debe tener máximo 200 caracteres",
    "cargo_dependencia": "Debe tener máximo 255 caracteres",
    "direccion": "Debe tener máximo 255 caracteres",
    "colonia": "Debe tener máximo 150 caracteres",
    "municipio_alcaldia": "Debe tener máximo 100 caracteres",
    "estado": "Debe tener máximo 100 caracteres",
    "codigo_postal": "Debe tener entre 4 y 6 caracteres",
    "numero_volante": "Debe tener entre 15 y 25 caracteres",
    "extras": "Debe tener máximo 420 caracteres",
    "contacto": "Debe tener máximo 150 caracteres",
    "indicaciones": "Debe tener máximo 200 caracteres",
    "observaciones_ia": "Debe tener máximo 100 caracteres",
}


def _validation_message(field: str, error: dict[str, Any]) -> str:
    error_type = str(error.get("type", ""))
    if error_type in {"string_too_short", "string_too_long"}:
        return _LENGTH_MESSAGES.get(field, "Longitud inválida")
    if error_type == "missing":
        return "Campo obligatorio"
    if error_type == "literal_error":
        expected = error.get("ctx", {}).get("expected", "")
        return f"Debe ser uno de: {expected}" if expected else "Valor no permitido"
    if error_type in {"greater_than_equal", "int_parsing", "int_type"}:
        if error_type == "greater_than_equal":
            return "Debe ser mayor o igual a 0"
        return "Debe ser un número entero"
    return str(error.get("msg", "Valor inválido"))


def validate_registro(data: dict[str, Any]) -> tuple[RegistroRequest | None, list[RegistroFieldError]]:
    """Valida todos los campos y devuelve todos los errores encontrados."""
    try:
        return RegistroRequest.model_validate(data), []
    except ValidationError as exc:
        errors: list[RegistroFieldError] = []
        for detail in exc.errors():
            field = ".".join(str(part) for part in detail.get("loc", ())) or "registro"
            errors.append({
                "campo": field,
                "error": _validation_message(field, detail),
            })
        return None, errors
