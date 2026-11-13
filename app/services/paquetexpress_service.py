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
from app.models.receiver import (
    AddressDto,
    ContactDto,
    ReceiverDto,
    contact_display_line,
    receiver_display_name,
    receiver_position_line,
    shipment_receiver_name,
)
from app.models.shipping import (
    CoverageItem,
    ShippingDto,
    ShippingFieldError,
    ShippingRequest,
    validate_shipping,
)
from app.services.auth_service import get_access_token

DEFAULT_SHIPMENT_EMAIL = "notificaciones@feuh.com.mx"


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


def _join_non_empty(*values: Any, sep: str = " ") -> str:
    parts = [str(value or "").strip() for value in values]
    return sep.join(part for part in parts if part)


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
        "name_receiver": _join_non_empty(
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
        "email": DEFAULT_SHIPMENT_EMAIL,
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


def _phone_from_contact(contact: ContactDto | None) -> str | None:
    """Teléfono del envío: solo los dígitos del número, sin extensión."""
    if contact is None:
        return None
    digits = re.sub(r"\D", "", contact.phone or "")
    if 10 <= len(digits) <= 20:
        return digits
    return None


def build_shipment_payload_from_receiver(
    receiver: ReceiverDto,
    address: AddressDto,
    coverage: CoverageItem,
    package_extras: dict[str, Any],
    contact: ContactDto | None = None,
) -> dict[str, Any]:
    """Arma el body plano de ``POST /shipments-px/``.

    Colonia, código postal, ciudad, estado y tipo salen de la cobertura
    Paquetexpress. El nombre y la calle salen del destinatario y del domicilio
    elegido. El teléfono es el del contacto seleccionado, sin extensión. El
    correo del destinatario no se usa: va el del formulario de envío.
    """
    name = shipment_receiver_name(receiver).strip()[:80]

    chosen = contact
    if chosen is None and receiver.contacts:
        chosen = receiver.contacts[0]
    phone = _phone_from_contact(chosen)

    reference = str(address.address_reference or "").strip() or None
    payload: dict[str, Any] = dict(package_extras)
    payload.update(
        {
            "name_receiver": name,
            "country": address.country,
            "street": address.street,
            "num_street": address.num_street,
            "address_reference": reference,
            "phone": phone,
            "state": coverage.state,
            "city": coverage.city,
            "colony": coverage.colony,
            "postal_code": coverage.postal_code,
            "coverage_type": coverage.coverage_type,
        }
    )
    if not str(payload.get("email") or "").strip():
        payload["email"] = DEFAULT_SHIPMENT_EMAIL
    return payload


def _persona_cargo_line(receiver: ReceiverDto) -> str:
    """Abreviatura del cargo, nombre de la dependencia y su estado."""
    if receiver.position is None:
        return ""
    role = ""
    if receiver.position.job_role is not None:
        role = receiver.position.job_role.abbreviation.strip()
    organization = receiver.position.organization
    return " ".join(
        part
        for part in (
            role,
            organization.name.strip(),
            organization.state.strip(),
        )
        if part
    )


def record_from_existing_shipment(
    receiver: ReceiverDto,
    address: AddressDto,
    coverage: CoverageItem,
    contact: ContactDto | None = None,
) -> dict[str, Any]:
    """Campos de registro a partir de lo elegido para el envío.

    ``numero_volante`` queda vacío: no se sabe cuál volante corresponde.
    """
    cargo = receiver_position_line(receiver).strip()
    if receiver.type_entity == "PERSONA":
        name = receiver_display_name(receiver).strip()
        cargo_field = _persona_cargo_line(receiver)
    elif receiver.type_entity == "GOBIERNO":
        name = cargo
        cargo_field = ""
    else:
        name = shipment_receiver_name(receiver).strip()
        cargo_field = cargo
    street = " ".join(
        part.strip()
        for part in (address.street or "", address.num_street or "")
        if part and part.strip()
    )
    phone = contact_display_line(contact).strip() if contact is not None else ""
    if phone == "Sin teléfono":
        phone = ""
    reference = str(address.address_reference or "").strip()
    campos = {
        "nombre_titulo": name,
        "cargo_dependencia": cargo_field,
        "direccion": street,
        "colonia": str(coverage.colony or "").strip(),
        "municipio_alcaldia": str(address.municipality or "").strip(),
        "estado": str(coverage.state or "").strip(),
        "codigo_postal": str(coverage.postal_code or "").strip(),
        "numero_volante": "",
        "extras": "",
        "contacto": phone,
        "indicaciones": reference,
    }
    lines = [
        name,
        cargo_field,
        street,
        campos["colonia"],
        campos["municipio_alcaldia"],
        campos["estado"],
        campos["codigo_postal"],
        phone,
        reference,
    ]
    raw = "\n".join(line for line in lines if line)
    if len(raw) < 40:
        raw = f"{raw}\nRegistro del envío con destinatario existente.".strip()
    return {
        "destinatario_raw": raw[:660],
        "campos": campos,
        "observaciones_ia": "",
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

def list_shipments_by_date_range(
    desde: datetime,
    hasta: datetime,
    my_shipments: bool = False,
) -> list[ShippingDto]:
    """Lista los envíos de fechas entre desde y hasta.

    ``my_shipments=True`` limita el resultado a los del usuario en sesión.
    """
    token = _required_token()
    try:
        return list_by_date_range(desde, hasta, token, my_shipments=my_shipments)
    except ShipmentsSessionExpiredError as exc:
        raise PaquetexpressSessionExpiredError(str(exc)) from exc
    except ShipmentsApiError as exc:
        raise PaquetexpressServiceError(str(exc)) from exc
