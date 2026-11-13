"""Listado y alta genéricos de los catálogos del directorio.

Cada módulo (títulos, cargos, organizaciones, volantes) publica sus propias
excepciones y delega aquí el HTTP.
"""

from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from app.api.http_support import (
    SessionExpiredError,
    TransportError,
    error_detail,
    json_body,
    query_params,
    request,
    validation_errors,
)
from app.config import api_abs_url
from app.models.receiver import Paginated

T = TypeVar("T", bound=BaseModel)


def list_items(
    token: str,
    endpoint: str,
    item_type: type[T],
    *,
    search: str | None = None,
    page: int = 1,
    page_size: int = 20,
    extra: dict[str, Any] | None = None,
    api_error: type[Exception],
    session_error: type[Exception],
    validation_error: type[Exception],
) -> Paginated[T]:
    params = query_params(search=search, page=page, page_size=page_size, **(extra or {}))
    response = _call(
        "GET",
        api_abs_url(endpoint),
        token,
        api_error=api_error,
        session_error=session_error,
        params=params,
    )
    if response.status_code == 422:
        raise validation_error(validation_errors(response))
    if response.status_code >= 400:
        raise api_error(
            f"No se pudo consultar el catálogo (código {response.status_code}): "
            f"{error_detail(response)}"
        )
    payload = json_body(response)
    if not isinstance(payload, dict):
        raise api_error("La API devolvió un formato inesperado: se esperaba un objeto.")
    try:
        return Paginated[item_type].model_validate(payload)
    except ValidationError as exc:
        raise api_error(f"El catálogo tiene formato inválido. {exc}") from exc


def create_item(
    token: str,
    endpoint: str,
    item_type: type[T],
    payload: dict[str, Any],
    *,
    api_error: type[Exception],
    session_error: type[Exception],
    conflict_error: type[Exception],
    validation_error: type[Exception],
) -> T:
    response = _call(
        "POST",
        api_abs_url(endpoint),
        token,
        api_error=api_error,
        session_error=session_error,
        json_body=payload,
    )
    if response.status_code == 409:
        raise conflict_error(error_detail(response))
    if response.status_code == 422:
        raise validation_error(validation_errors(response))
    if response.status_code >= 400:
        raise api_error(
            f"No se pudo crear el registro (código {response.status_code}): "
            f"{error_detail(response)}"
        )
    body = json_body(response)
    if not isinstance(body, dict):
        raise api_error("La API devolvió un formato inesperado: se esperaba un objeto.")
    try:
        return item_type.model_validate(body)
    except ValidationError as exc:
        raise api_error(f"El registro tiene formato inválido. {exc}") from exc


def _call(method: str, url: str, token: str, *, api_error: type[Exception], session_error: type[Exception], **kwargs: Any):
    try:
        return request(method, url, token, **kwargs)
    except TransportError as exc:
        raise api_error(str(exc)) from exc
    except SessionExpiredError as exc:
        raise session_error(str(exc)) from exc
