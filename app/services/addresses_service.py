"""Alta de un domicilio para un destinatario que ya existe."""

from __future__ import annotations

from typing import Any

from app.api import addresses_api
from app.models.receiver import AddressDto, present_api_errors, validate_address
from app.services.auth_service import get_access_token


class AddressServiceError(Exception):
    """Error de dominio al crear un domicilio."""


class AddressSessionExpiredError(AddressServiceError):
    """No hay sesión o la API devolvió 401."""


class AddressDuplicateError(AddressServiceError):
    """Ya hay un domicilio equivalente. Incluye su id."""

    def __init__(self, address_id: int, message: str = "El destinatario ya tiene un domicilio equivalente"):
        self.address_id = address_id
        super().__init__(message)


class AddressValidationError(AddressServiceError):
    """Errores acumulados del formulario de domicilio."""

    def __init__(self, errors: list[dict[str, str]]):
        self.errors = errors
        super().__init__("El domicilio contiene campos inválidos.")


def _required_token() -> str:
    token = get_access_token()
    if not token:
        raise AddressSessionExpiredError(
            "No hay sesión activa. Inicie sesión de nuevo."
        )
    return token


def _clean(value: Any) -> str:
    return str(value or "").strip()


def build_address_payload(form_data: dict[str, Any]) -> dict[str, Any]:
    reference = _clean(form_data.get("address_reference"))
    payload = {
        "street": _clean(form_data.get("street")),
        "num_street": _clean(form_data.get("num_street")),
        "colony": _clean(form_data.get("colony")),
        "municipality": _clean(form_data.get("municipality")),
        "city": _clean(form_data.get("city")),
        "state": _clean(form_data.get("state")),
        "postal_code": _clean(form_data.get("postal_code")),
        "country": _clean(form_data.get("country")) or "MEXICO",
    }
    if reference:
        payload["address_reference"] = reference
    return payload


def build_address_update_payload(
    form_data: dict[str, Any],
    original: AddressDto,
) -> dict[str, Any]:
    """Solo las claves que cambiaron. ``address_reference: null`` borra la referencia."""
    current = build_address_payload(form_data)
    changed: dict[str, Any] = {}
    for key in (
        "street",
        "num_street",
        "colony",
        "municipality",
        "city",
        "state",
        "postal_code",
        "country",
    ):
        new = current.get(key, "")
        old = getattr(original, key) or ""
        if new != old:
            changed[key] = new
    new_ref = current.get("address_reference") or None
    old_ref = original.address_reference or None
    if new_ref != old_ref:
        changed["address_reference"] = new_ref
    return changed


def create_address(receiver_id: int, form_data: dict[str, Any]) -> AddressDto:
    """Valida y crea el domicilio del destinatario indicado."""
    payload = build_address_payload(form_data)
    model, errors = validate_address(payload)
    if errors or model is None:
        raise AddressValidationError(errors)
    token = _required_token()
    try:
        return addresses_api.create_address(
            receiver_id,
            model.model_dump(mode="json", exclude_none=True),
            token,
        )
    except addresses_api.AddressDuplicateError as exc:
        raise AddressDuplicateError(exc.address_id, str(exc)) from exc
    except addresses_api.AddressesSessionExpiredError as exc:
        raise AddressSessionExpiredError(str(exc)) from exc
    except addresses_api.AddressesValidationError as exc:
        raise AddressValidationError(present_api_errors(exc.errors)) from exc
    except addresses_api.AddressesApiError as exc:
        raise AddressServiceError(str(exc)) from exc


def update_address(address_id: int, form_data: dict[str, Any], original: AddressDto) -> AddressDto:
    """Valida el formulario y envía solo las claves cambiadas."""
    payload = build_address_payload(form_data)
    model, errors = validate_address(payload)
    if errors or model is None:
        raise AddressValidationError(errors)
    body = build_address_update_payload(form_data, original)
    token = _required_token()
    try:
        return addresses_api.patch_address(address_id, body, token)
    except addresses_api.AddressDuplicateError as exc:
        raise AddressDuplicateError(exc.address_id, str(exc)) from exc
    except addresses_api.AddressesSessionExpiredError as exc:
        raise AddressSessionExpiredError(str(exc)) from exc
    except addresses_api.AddressesValidationError as exc:
        raise AddressValidationError(present_api_errors(exc.errors)) from exc
    except addresses_api.AddressesApiError as exc:
        raise AddressServiceError(str(exc)) from exc
