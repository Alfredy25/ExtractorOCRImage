"""Modelos y validación acumulativa para envíos Paquetexpress."""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional, TypedDict
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, ValidationError, field_validator, ConfigDict


class CoverageItem(BaseModel):
    """Elemento de cobertura devuelto por ``GET /coverages/{cp}``."""

    postal_code: str
    colony: str
    municipality: str
    city: str
    state: str
    coverage_type: str


class ShippingRequest(BaseModel):
    """Cuerpo esperado por ``POST /shipments-px/``."""

    name_receiver: str = Field(..., min_length=4, max_length=80)
    rfc: str = Field(..., min_length=12, max_length=15)
    country: str = Field(..., min_length=3, max_length=50)
    state: str = Field(..., min_length=5, max_length=60)
    city: str = Field(..., min_length=3, max_length=60)
    colony: str = Field(..., min_length=3, max_length=60)
    street: str = Field(..., min_length=3, max_length=80)
    num_street: str = Field(..., min_length=1, max_length=15)
    postal_code: str = Field(..., min_length=4, max_length=5, pattern=r"^[0-9]+$")
    email: Optional[EmailStr] = Field(default=None)
    phone: Optional[str] = Field(default=None, min_length=10, max_length=20)
    address_reference: Optional[str] = Field(default=None, max_length=50)
    quantity: int = Field(..., ge=1)
    package_code: int = Field(..., ge=1, le=63)
    content: str = Field(..., min_length=10, max_length=100)
    weight: Decimal = Field(..., gt=0, max_digits=8, decimal_places=2)
    length: Decimal = Field(..., gt=0, max_digits=8, decimal_places=2)
    width: Decimal = Field(..., gt=0, max_digits=8, decimal_places=2)
    height: Decimal = Field(..., gt=0, max_digits=8, decimal_places=2)
    coverage_type: str = Field(..., min_length=4, max_length=60)
    comments: Optional[str] = Field(default=None, min_length=5, max_length=80)

    @field_validator("email")
    @classmethod
    def _email_max_length(cls, value: EmailStr | None) -> EmailStr | None:
        if value is not None and len(str(value)) > 80:
            raise ValueError("Debe tener máximo 80 caracteres")
        return value


class ShippingDto(BaseModel):
    """DTO de envío devuelto por ``GET /shipments-px/``."""
    id_shipping: int = Field(..., examples=[1])
    id_folio: int = Field(default=..., examples=[1])

    name_receiver: str = Field(..., examples=["DR. LUCAS PINEDO PINEDO"])
    rfc: str = Field(..., examples=["XAXX010101000"])
    country: str = Field(..., examples=["MEXICO"])
    state: str = Field(..., examples=["ZACATECAS"])
    city: str = Field(..., examples=["CIUDAD GOBIERNO"])
    colony: str = Field(..., examples=["LOS ANGELES"])
    street: str = Field(..., examples=["CTO. CERRO DEL GATO"])
    num_street: str = Field(..., examples=["20"])
    postal_code: str = Field(..., examples=["98160"])

    email: Optional[EmailStr] = Field(default=None, examples=["destinatario@example.com"])
    phone: Optional[str] = Field(default=None, examples=["55 5555 5555"])
    address_reference: Optional[str] = Field(default=None)

    quantity: int = Field(..., examples=[1])
    package_code: int = Field(..., examples=[1])
    content: str = Field(..., examples=["Documentos Legales"])

    weight: Decimal = Field(..., examples=["1.00"])
    length: Decimal = Field(..., examples=["30.00"])
    width: Decimal = Field(..., examples=["20.00"])
    height: Decimal = Field(..., examples=["10.00"])
    coverage_type: Optional[str] = Field(default=None, examples=["PAQUETEXPRESS"])
    comments: Optional[str] = Field(default=None, examples=["ENTREGAR EN OFICIALIA DE PARTES O RECEPCION EN UN HORARIO DE 09:00 A 14:00 HRS."])
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ShippingFieldError(TypedDict):
    """Error de validación de envío presentable al usuario."""

    campo: str
    error: str


_LENGTH_MESSAGES = {
    "name_receiver": "Debe tener entre 4 y 80 caracteres",
    "rfc": "Debe tener entre 12 y 15 caracteres",
    "country": "Debe tener entre 3 y 50 caracteres",
    "state": "Debe tener entre 5 y 50 caracteres",
    "city": "Debe tener entre 3 y 60 caracteres",
    "colony": "Debe tener entre 3 y 60 caracteres",
    "street": "Debe tener entre 3 y 80 caracteres",
    "num_street": "Debe tener entre 1 y 15 caracteres",
    "postal_code": "Debe tener entre 4 y 5 caracteres",
    "phone": "Debe tener entre 10 y 20 caracteres",
    "address_reference": "Debe tener máximo 50 caracteres",
    "content": "Debe tener entre 10 y 100 caracteres",
    "coverage_type": "Debe tener entre 4 y 60 caracteres",
    "comments": "Debe tener entre 5 y 80 caracteres",
}

_FIELD_LABELS = {
    "name_receiver": "Destinatario",
    "rfc": "RFC",
    "country": "País",
    "state": "Estado",
    "city": "Ciudad",
    "colony": "Colonia",
    "street": "Calle",
    "num_street": "Número exterior",
    "postal_code": "Código Postal",
    "email": "Email",
    "phone": "Teléfono",
    "address_reference": "Referencia de domicilio",
    "quantity": "Cantidad",
    "package_code": "Código de paquete",
    "content": "Contenido",
    "weight": "Peso (kg)",
    "length": "Largo (cm)",
    "width": "Ancho (cm)",
    "height": "Alto (cm)",
    "coverage_type": "Tipo de cobertura",
    "comments": "Comentarios",
}


def _validation_message(field: str, error: dict[str, Any]) -> str:
    error_type = str(error.get("type", ""))
    if error_type in {"string_too_short", "string_too_long"}:
        return _LENGTH_MESSAGES.get(field, "Longitud inválida")
    if error_type == "string_pattern_mismatch":
        return "Debe contener únicamente números"
    if error_type == "missing":
        return "Campo obligatorio"
    if error_type == "value_error":
        return str(error.get("msg", "Valor inválido"))
    if error_type in {"greater_than_equal", "greater_than"}:
        if field == "quantity":
            return "Debe ser mayor o igual a 1"
        if field in {"weight", "length", "width", "height"}:
            return "Debe ser mayor a 0"
        return "Debe ser mayor o igual al valor mínimo permitido"
    if error_type == "less_than_equal":
        if field == "package_code":
            return "Debe estar entre 1 y 63"
        return "Debe ser menor o igual al valor máximo permitido"
    if error_type in {"int_parsing", "int_type"}:
        return "Debe ser un número entero"
    if error_type in {"decimal_parsing", "float_parsing", "float_type"}:
        return "Debe ser un número decimal válido"
    if error_type == "decimal_max_digits":
        return "Excede el máximo de 8 dígitos"
    if error_type == "decimal_max_places":
        return "Admite máximo 2 decimales"
    return str(error.get("msg", "Valor inválido"))


def validate_shipping(data: dict[str, Any]) -> tuple[ShippingRequest | None, list[ShippingFieldError]]:
    """Valida todos los campos del envío y acumula todos los errores."""
    try:
        return ShippingRequest.model_validate(data), []
    except ValidationError as exc:
        errors: list[ShippingFieldError] = []
        for detail in exc.errors():
            field = ".".join(str(part) for part in detail.get("loc", ())) or "shipping"
            errors.append({
                "campo": _FIELD_LABELS.get(field, field),
                "error": _validation_message(field, detail),
            })
        return None, errors
