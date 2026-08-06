"""Fachada de negocio para consulta de coberturas y creación de envíos PX."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.api.coverages_api import (
    CoverageNotFoundError,
    CoveragesApiError,
    CoveragesSessionExpiredError,
    get_coverages,
)
from app.api.shipments_api import (
    ShipmentsApiError,
    ShipmentsSessionExpiredError,
    create_shipment as api_create_shipment,
)
from app.models.shipping import CoverageItem, ShippingFieldError, validate_shipping
from app.services.auth_service import get_access_token


class PaquetexpressServiceError(Exception):
    """Error de dominio del flujo Paquetexpress."""


class PaquetexpressSessionExpiredError(PaquetexpressServiceError):
    """No hay sesión o la API devolvió 401."""


class PaquetexpressCoverageNotFoundError(PaquetexpressServiceError):
    """No se encontró cobertura para el código postal."""


class PaquetexpressValidationError(PaquetexpressServiceError):
    """Errores de validación acumulados para crear envío."""

    def __init__(self, errors: list[ShippingFieldError]):
        self.errors = errors
        super().__init__("El envío contiene campos inválidos.")


def _required_token() -> str:
    token = get_access_token()
    if not token:
        raise PaquetexpressSessionExpiredError(
            "No hay sesión activa. Inicie sesión de nuevo."
        )
    return token


def _first_non_empty(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _to_optional_string(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _to_coverage_item(item: dict[str, Any]) -> CoverageItem | None:
    try:
        return CoverageItem.model_validate(item)
    except Exception:
        return None


def get_coverages_for_postal_code(postal_code: str) -> list[CoverageItem]:
    """Obtiene coberturas tipadas para un código postal."""
    token = _required_token()
    try:
        raw = get_coverages(postal_code, token)
    except CoverageNotFoundError as exc:
        raise PaquetexpressCoverageNotFoundError(str(exc)) from exc
    except CoveragesSessionExpiredError as exc:
        raise PaquetexpressSessionExpiredError(str(exc)) from exc
    except CoveragesApiError as exc:
        raise PaquetexpressServiceError(str(exc)) from exc

    items = [_to_coverage_item(item) for item in raw]
    valid_items = [item for item in items if item is not None]
    if not valid_items:
        raise PaquetexpressServiceError(
            "La API devolvió coberturas con formato no reconocido."
        )
    return valid_items


def build_shipment_draft(
    ocr_form_data: dict[str, Any],
    coverage: CoverageItem,
) -> dict[str, Any]:
    """Arma los valores iniciales del formulario de envío desde OCR + cobertura."""
    campos = ocr_form_data.get("campos") or {}
    return {
        "name_receiver": _first_non_empty(
            campos.get("nombre_titulo"),
            campos.get("cargo_dependencia"),
        ),
        "rfc": "XAXX010101000",
        "country": "MEXICO",
        "state": coverage.state,
        "city": coverage.city,
        "colony": coverage.colony,
        "street": str(campos.get("direccion") or "").strip(),
        "num_street": "",
        "postal_code": coverage.postal_code,
        "email": "",
        "phone": str(campos.get("contacto") or "").strip(),
        "address_reference": str(campos.get("indicaciones") or "").strip(),
        "quantity": "1",
        "package_code": "1",
        "content": "DOCUMENTOS LEGALES",
        "weight": "1",
        "length": "30",
        "width": "20",
        "height": "1",
        "coverage_type": coverage.coverage_type,
    }


def _normalize_shipment_form(data: dict[str, Any]) -> dict[str, Any]:
    normalized = {
        "name_receiver": str(data.get("name_receiver") or "").strip(),
        "rfc": str(data.get("rfc") or "").strip(),
        "country": str(data.get("country") or "").strip(),
        "state": str(data.get("state") or "").strip(),
        "city": str(data.get("city") or "").strip(),
        "colony": str(data.get("colony") or "").strip(),
        "street": str(data.get("street") or "").strip(),
        "num_street": str(data.get("num_street") or "").strip(),
        "postal_code": str(data.get("postal_code") or "").strip(),
        "email": _to_optional_string(data.get("email")),
        "phone": _to_optional_string(data.get("phone")),
        "address_reference": _to_optional_string(data.get("address_reference")),
        "quantity": data.get("quantity"),
        "package_code": data.get("package_code"),
        "content": str(data.get("content") or "").strip(),
        "weight": data.get("weight"),
        "length": data.get("length"),
        "width": data.get("width"),
        "height": data.get("height"),
        "coverage_type": str(data.get("coverage_type") or "").strip(),
    }
    return normalized


def validate_shipment_form(data: dict[str, Any]) -> list[ShippingFieldError]:
    """Valida acumulativamente todos los campos del formulario de envío."""
    normalized = _normalize_shipment_form(data)
    _, errors = validate_shipping(normalized)
    return errors


def _parse_decimal_for_payload(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value).strip())


def create_shipment(data: dict[str, Any]) -> dict[str, Any]:
    """Valida y crea un envío Paquetexpress."""
    normalized = _normalize_shipment_form(data)
    model, errors = validate_shipping(normalized)
    if errors:
        raise PaquetexpressValidationError(errors)
    assert model is not None

    token = _required_token()
    payload = model.model_dump(exclude_none=True)
    payload["quantity"] = int(payload["quantity"])
    payload["package_code"] = int(payload["package_code"])
    payload["weight"] = _parse_decimal_for_payload(payload["weight"])
    payload["length"] = _parse_decimal_for_payload(payload["length"])
    payload["width"] = _parse_decimal_for_payload(payload["width"])
    payload["height"] = _parse_decimal_for_payload(payload["height"])
    payload["weight"] = f"{payload['weight']:.2f}"
    payload["length"] = f"{payload['length']:.2f}"
    payload["width"] = f"{payload['width']:.2f}"
    payload["height"] = f"{payload['height']:.2f}"

    try:
        return api_create_shipment(payload, token)
    except ShipmentsSessionExpiredError as exc:
        raise PaquetexpressSessionExpiredError(str(exc)) from exc
    except ShipmentsApiError as exc:
        raise PaquetexpressServiceError(str(exc)) from exc
