"""Transporte HTTP del catálogo SEPOMEX."""

from __future__ import annotations

from pydantic import ValidationError

from app.api.http_support import (
    SessionExpiredError,
    TransportError,
    error_detail,
    json_body,
    request,
)
from app.config import SEPOMEX_ENDPOINT, api_abs_url
from app.models.sepomex import SepomexDto


class SepomexApiError(Exception):
    """Fallo HTTP al consultar SEPOMEX."""


class SepomexSessionExpiredError(SepomexApiError):
    """El backend rechazó el JWT con estado 401."""


class SepomexNotFoundError(SepomexApiError):
    """El código postal no está en el catálogo."""


def get_sepomex(postal_code: str, token: str) -> list[SepomexDto]:
    """Consulta los asentamientos de un código postal de 5 dígitos."""
    url = api_abs_url(f"{SEPOMEX_ENDPOINT.rstrip('/')}/{postal_code}")
    try:
        response = request("GET", url, token)
    except TransportError as exc:
        raise SepomexApiError(str(exc)) from exc
    except SessionExpiredError as exc:
        raise SepomexSessionExpiredError(str(exc)) from exc

    if response.status_code == 404:
        raise SepomexNotFoundError(error_detail(response))
    if response.status_code >= 400:
        raise SepomexApiError(
            f"No se pudo consultar SEPOMEX (código {response.status_code}): "
            f"{error_detail(response)}"
        )
    payload = json_body(response)
    if not isinstance(payload, list):
        raise SepomexApiError("La API devolvió un formato inesperado: se esperaba una lista.")
    try:
        return [SepomexDto.model_validate(item) for item in payload]
    except ValidationError as exc:
        raise SepomexApiError(f"El catálogo SEPOMEX tiene formato inválido. {exc}") from exc
