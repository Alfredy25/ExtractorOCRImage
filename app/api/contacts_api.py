"""Transporte HTTP para crear un contacto de un destinatario existente."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from app.api.http_support import (
    SessionExpiredError,
    TransportError,
    error_detail,
    json_body,
    request,
    validation_errors,
)
from app.config import CONTACTS_ENDPOINT, api_abs_url
from app.models.receiver import ContactDto


class ContactsApiError(Exception):
    """Fallo HTTP al crear un contacto."""


class ContactsSessionExpiredError(ContactsApiError):
    """El backend rechazó el JWT con estado 401."""


class ContactDuplicateError(ContactsApiError):
    """El destinatario ya tiene ese teléfono y esa extensión."""

    def __init__(
        self,
        message: str = "El destinatario ya tiene un contacto con ese teléfono y extensión",
    ):
        super().__init__(message)


class ContactsValidationError(ContactsApiError):
    """El contacto no pasó la validación del servidor."""

    def __init__(self, errors: list[dict[str, str]]):
        self.errors = errors
        super().__init__("El contacto contiene campos inválidos.")


def _call(method: str, url: str, token: str, **kwargs: Any):
    try:
        return request(method, url, token, **kwargs)
    except TransportError as exc:
        raise ContactsApiError(str(exc)) from exc
    except SessionExpiredError as exc:
        raise ContactsSessionExpiredError(str(exc)) from exc


def _parse_contact(body: Any) -> ContactDto:
    if not isinstance(body, dict):
        raise ContactsApiError("La API devolvió un formato inesperado: se esperaba un objeto.")
    try:
        return ContactDto.model_validate(body)
    except ValidationError as exc:
        raise ContactsApiError(f"El contacto tiene formato inválido. {exc}") from exc


def create_contact(receiver_id: int, payload: dict[str, Any], token: str) -> ContactDto:
    """``POST /contacts/{receiver_id}``."""
    url = api_abs_url(f"{CONTACTS_ENDPOINT.rstrip('/')}/{receiver_id}")
    response = _call("POST", url, token, json_body=payload)
    if response.status_code == 409:
        raise ContactDuplicateError(error_detail(response))
    if response.status_code == 422:
        raise ContactsValidationError(validation_errors(response))
    if response.status_code >= 400:
        raise ContactsApiError(
            f"No se pudo crear el contacto (código {response.status_code}): "
            f"{error_detail(response)}"
        )
    return _parse_contact(json_body(response))
