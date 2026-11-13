"""Transporte HTTP para crear un domicilio de un destinatario existente."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from app.api.http_support import (
    SessionExpiredError,
    TransportError,
    duplicate_id,
    error_detail,
    json_body,
    request,
    validation_errors,
)
from app.config import ADDRESSES_ENDPOINT, api_abs_url
from app.models.receiver import AddressDto


class AddressesApiError(Exception):
    """Fallo HTTP al crear un domicilio."""


class AddressesSessionExpiredError(AddressesApiError):
    """El backend rechazó el JWT con estado 401."""


class AddressDuplicateError(AddressesApiError):
    """El destinatario ya tiene un domicilio equivalente."""

    def __init__(self, address_id: int, message: str = "El destinatario ya tiene un domicilio equivalente"):
        self.address_id = address_id
        super().__init__(message)


class AddressesValidationError(AddressesApiError):
    """El domicilio no pasó la validación del servidor."""

    def __init__(self, errors: list[dict[str, str]]):
        self.errors = errors
        super().__init__("El domicilio contiene campos inválidos.")


def _call(method: str, url: str, token: str, **kwargs: Any):
    try:
        return request(method, url, token, **kwargs)
    except TransportError as exc:
        raise AddressesApiError(str(exc)) from exc
    except SessionExpiredError as exc:
        raise AddressesSessionExpiredError(str(exc)) from exc


def create_address(receiver_id: int, payload: dict[str, Any], token: str) -> AddressDto:
    """``POST /addresses/{receiver_id}``."""
    url = api_abs_url(f"{ADDRESSES_ENDPOINT.rstrip('/')}/{receiver_id}")
    response = _call("POST", url, token, json_body=payload)
    if response.status_code == 409:
        found = duplicate_id(response, "address_id")
        if found is None:
            raise AddressesApiError(error_detail(response))
        raise AddressDuplicateError(found, error_detail(response))
    if response.status_code == 422:
        raise AddressesValidationError(validation_errors(response))
    if response.status_code >= 400:
        raise AddressesApiError(
            f"No se pudo crear el domicilio (código {response.status_code}): "
            f"{error_detail(response)}"
        )
    return _parse_address(json_body(response))


def _parse_address(body: Any) -> AddressDto:
    if not isinstance(body, dict):
        raise AddressesApiError("La API devolvió un formato inesperado: se esperaba un objeto.")
    try:
        return AddressDto.model_validate(body)
    except ValidationError as exc:
        raise AddressesApiError(f"El domicilio tiene formato inválido. {exc}") from exc


def patch_address(address_id: int, payload: dict[str, Any], token: str) -> AddressDto:
    """``PATCH /addresses/{address_id}``. Solo aplica las claves enviadas."""
    url = api_abs_url(f"{ADDRESSES_ENDPOINT.rstrip('/')}/{address_id}")
    response = _call("PATCH", url, token, json_body=payload)
    if response.status_code == 409:
        found = duplicate_id(response, "address_id")
        if found is None:
            raise AddressesApiError(error_detail(response))
        raise AddressDuplicateError(found, error_detail(response))
    if response.status_code == 422:
        raise AddressesValidationError(validation_errors(response))
    if response.status_code >= 400:
        raise AddressesApiError(
            f"No se pudo actualizar el domicilio (código {response.status_code}): "
            f"{error_detail(response)}"
        )
    return _parse_address(json_body(response))
