"""Fachada de negocio para consulta de coberturas y creación de envíos PX."""

from __future__ import annotations
import re

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
    list_by_date_range,
    update_shipment as api_update_shipment,
)
from datetime import datetime
from app.models.shipping import (
    CoverageItem,
    ShippingDto,
    ShippingFieldError,
    ShippingRequest,
    validate_shipping,
)
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


def build_shipment_draft(ocr_form_data: dict[str, Any], coverage: CoverageItem) -> dict[str, Any]:
    """Arma los valores iniciales del formulario de envío desde OCR + cobertura."""
    campos = ocr_form_data.get("campos") or {}
    return {
        "name_receiver": _first_non_empty(
            campos.get("nombre_titulo"),
            campos.get("cargo_dependencia"),
        ),
        "rfc": "XAXX-010101-000",
        "country": "MEXICO",
        "state": coverage.state,
        "city": coverage.city,
        "colony": coverage.colony,
        "street": str(campos.get("direccion") or "").strip(),
        "num_street": "",
        "postal_code": coverage.postal_code,
        "email": "notificaciones@feuh.com.mx",
        "phone": _first_non_empty(campos.get("contacto"), "55 7586 8462"),
        "address_reference": str(campos.get("indicaciones") or "").strip(),
        "quantity": "1",
        "package_code": "1",
        "content": "DOCUMENTOS LEGALES",
        "comments": "ENTREGAR EN OFICIALIA DE PARTES O RECEPCION EN UN HORARIO DE 09:00 A 14:00 HRS.",
        "weight": "0.5",
        "length": "30",
        "width": "24",
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
        "comments": _to_optional_string(data.get("comments")),
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


def _payload_from_shipping_request(model: ShippingRequest) -> dict[str, Any]:
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
    return payload


def create_shipment(data: dict[str, Any]) -> dict[str, Any]:
    """Valida y crea un envío Paquetexpress."""
    normalized = _normalize_shipment_form(data)
    model, errors = validate_shipping(normalized)
    if errors:
        raise PaquetexpressValidationError(errors)
    assert model is not None

    token = _required_token()
    payload = _payload_from_shipping_request(model)

    try:
        return api_create_shipment(payload, token)
    except ShipmentsSessionExpiredError as exc:
        raise PaquetexpressSessionExpiredError(str(exc)) from exc
    except ShipmentsApiError as exc:
        raise PaquetexpressServiceError(str(exc)) from exc


def update_shipment(id_shipping: int, data: dict[str, Any]) -> ShippingDto:
    """Valida y actualiza un envío Paquetexpress."""
    normalized = _normalize_shipment_form(data)
    model, errors = validate_shipping(normalized)
    if errors:
        raise PaquetexpressValidationError(errors)
    assert model is not None

    token = _required_token()
    payload = _payload_from_shipping_request(model)

    try:
        return api_update_shipment(id_shipping, payload, token)
    except ShipmentsSessionExpiredError as exc:
        raise PaquetexpressSessionExpiredError(str(exc)) from exc
    except ShipmentsApiError as exc:
        raise PaquetexpressServiceError(str(exc)) from exc

def list_shipments_by_date_range(desde: datetime, hasta: datetime) -> list[ShippingDto]:
    """Lista los envíos de fechas entre desde y hasta."""
    token = _required_token()
    try:
        return list_by_date_range(desde, hasta, token)
    except ShipmentsSessionExpiredError as exc:
        raise PaquetexpressSessionExpiredError(str(exc)) from exc
    except ShipmentsApiError as exc:
        raise PaquetexpressServiceError(str(exc)) from exc

replacements_vocales = {
    "Á": "A",
    "É": "E",
    "Í": "I",
    "Ó": "O",
    "Ú": "U",
    "/": "",
    ",": "",
    ".": ""
}

replacements_direcciones = {
    "AVENIDA": "AV",
    "BOULEVARD":"BLVD",
    "CARRETERA": "CARR",
    "CALLE": "C",
    "EDIFICIO": "EDIF"
}

replacements_cargos = {
    "MAESTRO": "MTRO",
    "MAESTRA": "MTRA",
    "PROFESORA": "PROFA",
    "PROFESOR": "PROF",
    "DIPUTADO": "DIP",
    "DIPUTADA": "DIP",
    "SENADOR": "SEN",
    "SENADORA": "SEN",
    "DOCTOR": "DR",
    "DOCTORA": "DRA",
    "TITULAR": "TIT",
    "SECRETARIO": "SEC",
    "PRESIDENTE": "PDTE",
    "PRESIDENTA": "PDTA",
    "ADMINISTRADORA": "ADMIN",
    "ADMINISTRADOR": "ADMIN",
    "GENERAL": "GRAL",
    "ORGANO INTERNO DE CONTROL": "OIC",
    "ORGANO DE CONTROL INTERNO": "OIC",
    "DIRECTOR": "DIR",
    "UNIVERSIDAD": "UNI",
    "AUTONOMA": "AUT",
    "SECRETARIO": "SEC",
    "GOBERNADOR": "GOB",
    }

def _replace_whole_words(text: str, mapping: dict[str, str]) -> str:
    if not text or not mapping:
        return text
    pattern = re.compile(
        r"\b(?:"
        + "|".join(re.escape(key) for key in sorted(mapping, key=len, reverse=True))
        + r")\b"
    )
    return pattern.sub(lambda match: mapping[match.group(0)], text)

def normalize_shipment_fields(data: dict[str, Any]) -> dict[str, Any]:
    """Normaliza una copia con campos limpios. No valida ni llama API"""

    # primero los convertimos a mayúsculas
    normalized = {
        "name_receiver": str(data.get("name_receiver") or "").strip().upper(),
        "street": str(data.get("street") or "").strip().upper(),
        "address_reference": str(data.get("address_reference") or "").strip().upper(),
    }

    # luego realizamos los reemplazos de las vocales
    for key, value in replacements_vocales.items():
        normalized["name_receiver"] = normalized["name_receiver"].replace(key, value)
        normalized["street"] = normalized["street"].replace(key, value)
        normalized["address_reference"] = normalized["address_reference"].replace(key, value)
    
    normalized["street"] = _replace_whole_words(normalized["street"], replacements_direcciones)
    normalized["address_reference"] = _replace_whole_words(normalized["address_reference"], replacements_direcciones)
    normalized["name_receiver"] = _replace_whole_words(normalized["name_receiver"], replacements_cargos)

    return normalized