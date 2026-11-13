"""Transporte HTTP para buscar y crear destinatarios."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from app.api.http_support import (
    SessionExpiredError,
    TransportError,
    duplicate_id,
    error_detail,
    json_body,
    query_params,
    request,
    validation_errors,
)
from app.config import RECEIVERS_ENDPOINT, api_abs_url
from app.models.receiver import Paginated, ReceiverDto


class ReceiversApiError(Exception):
    """Fallo HTTP al consultar o crear destinatarios."""


class ReceiversSessionExpiredError(ReceiversApiError):
    """El backend rechazó el JWT con estado 401."""


class ReceiverDuplicateError(ReceiversApiError):
    """Ya existe un destinatario equivalente. Incluye su id."""

    def __init__(self, receiver_id: int, message: str = "El destinatario ya existe"):
        self.receiver_id = receiver_id
        super().__init__(message)


class ReceiversValidationError(ReceiversApiError):
    """El cuerpo o la búsqueda no pasaron la validación del servidor."""

    def __init__(self, errors: list[dict[str, str]]):
        self.errors = errors
        super().__init__("El destinatario contiene campos inválidos.")


def _call(method: str, url: str, token: str, **kwargs: Any):
    try:
        return request(method, url, token, **kwargs)
    except TransportError as exc:
        raise ReceiversApiError(str(exc)) from exc
    except SessionExpiredError as exc:
        raise ReceiversSessionExpiredError(str(exc)) from exc


def _page(payload: Any) -> Paginated[ReceiverDto]:
    if not isinstance(payload, dict):
        raise ReceiversApiError("La API devolvió un formato inesperado: se esperaba un objeto.")
    try:
        return Paginated[ReceiverDto].model_validate(payload)
    except ValidationError as exc:
        raise ReceiversApiError(
            f"El listado de destinatarios tiene formato inválido. {exc}"
        ) from exc


def _receiver(payload: Any) -> ReceiverDto:
    if not isinstance(payload, dict):
        raise ReceiversApiError("La API devolvió un formato inesperado: se esperaba un objeto.")
    try:
        return ReceiverDto.model_validate(payload)
    except ValidationError as exc:
        raise ReceiversApiError(f"El destinatario tiene formato inválido. {exc}") from exc


def search_receivers(
    token: str,
    *,
    search: str | None = None,
    type_entity: str | None = None,
    state: str | None = None,
    page: int = 1,
    page_size: int = 10,
    order_by: str = "id",
    direction: str = "asc",
) -> Paginated[ReceiverDto]:
    """Lista destinatarios. ``query`` coincide con nombre u organización."""
    url = api_abs_url(RECEIVERS_ENDPOINT)
    params = query_params(
        query=search,
        type_entity=type_entity,
        state=state,
        page=page,
        page_size=page_size,
        order_by=order_by,
        direction=direction,
    )
    response = _call("GET", url, token, params=params)
    if response.status_code == 422:
        raise ReceiversValidationError(validation_errors(response))
    if response.status_code >= 400:
        raise ReceiversApiError(
            f"No se pudo buscar destinatarios (código {response.status_code}): "
            f"{error_detail(response)}"
        )
    return _page(json_body(response))


def create_receiver(payload: dict[str, Any], token: str) -> ReceiverDto:
    """Crea destinatario, domicilio y, si vienen, contacto, puesto y volante."""
    url = api_abs_url(RECEIVERS_ENDPOINT)
    response = _call("POST", url, token, json_body=payload)
    if response.status_code == 409:
        found = duplicate_id(response, "receiver_id")
        if found is None:
            raise ReceiversApiError(error_detail(response))
        raise ReceiverDuplicateError(found, error_detail(response))
    if response.status_code == 422:
        raise ReceiversValidationError(validation_errors(response))
    if response.status_code >= 400:
        raise ReceiversApiError(
            f"No se pudo crear el destinatario (código {response.status_code}): "
            f"{error_detail(response)}"
        )
    return _receiver(json_body(response))


def patch_receiver(receiver_id: int, payload: dict[str, Any], token: str) -> ReceiverDto:
    """``PATCH /receivers/{receiver_id}``. Solo aplica las claves enviadas."""
    url = api_abs_url(f"{RECEIVERS_ENDPOINT.rstrip('/')}/{receiver_id}")
    response = _call("PATCH", url, token, json_body=payload)
    if response.status_code == 409:
        found = duplicate_id(response, "receiver_id")
        if found is None:
            raise ReceiversApiError(error_detail(response))
        raise ReceiverDuplicateError(found, error_detail(response))
    if response.status_code == 422:
        raise ReceiversValidationError(validation_errors(response))
    if response.status_code >= 400:
        raise ReceiversApiError(
            f"No se pudo actualizar el destinatario (código {response.status_code}): "
            f"{error_detail(response)}"
        )
    return _receiver(json_body(response))
