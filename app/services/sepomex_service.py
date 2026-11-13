"""Consulta de asentamientos SEPOMEX por código postal."""

from __future__ import annotations

import re

from app.api import sepomex_api
from app.models.sepomex import SepomexDto
from app.services.auth_service import get_access_token


class SepomexServiceError(Exception):
    """Error de dominio al consultar SEPOMEX."""


class SepomexSessionExpiredError(SepomexServiceError):
    """No hay sesión o la API devolvió 401."""


class SepomexNotFoundError(SepomexServiceError):
    """El código postal no está en el catálogo."""


class SepomexValidationError(SepomexServiceError):
    """El código postal no tiene 5 dígitos."""


def _required_token() -> str:
    token = get_access_token()
    if not token:
        raise SepomexSessionExpiredError(
            "No hay sesión activa. Inicie sesión de nuevo."
        )
    return token


def fetch_sepomex(postal_code: str) -> list[SepomexDto]:
    """Devuelve los asentamientos del código postal."""
    cp = str(postal_code or "").strip()
    if re.fullmatch(r"\d{5}", cp) is None:
        raise SepomexValidationError("El código postal debe tener 5 dígitos.")
    token = _required_token()
    try:
        return sepomex_api.get_sepomex(cp, token)
    except sepomex_api.SepomexNotFoundError as exc:
        raise SepomexNotFoundError(str(exc)) from exc
    except sepomex_api.SepomexSessionExpiredError as exc:
        raise SepomexSessionExpiredError(str(exc)) from exc
    except sepomex_api.SepomexApiError as exc:
        raise SepomexServiceError(str(exc)) from exc
