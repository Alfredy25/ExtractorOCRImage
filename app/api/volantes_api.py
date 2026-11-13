"""Transporte HTTP de volantes."""

from __future__ import annotations

from typing import Any

from app.api.catalog_http import create_item, list_items
from app.config import VOLANTES_ENDPOINT
from app.models.receiver import Paginated, VolanteDto


class VolantesApiError(Exception):
    """Fallo HTTP de volantes."""


class VolantesSessionExpiredError(VolantesApiError):
    """El backend rechazó el JWT con estado 401."""


class VolantesConflictError(VolantesApiError):
    """El nombre del volante ya existe."""


class VolantesValidationError(VolantesApiError):
    """Query o cuerpo inválidos."""

    def __init__(self, errors: list[dict[str, str]]):
        self.errors = errors
        super().__init__("El volante contiene campos inválidos.")


def list_volantes(
    token: str,
    *,
    search: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> Paginated[VolanteDto]:
    return list_items(
        token,
        VOLANTES_ENDPOINT,
        VolanteDto,
        search=search,
        page=page,
        page_size=page_size,
        api_error=VolantesApiError,
        session_error=VolantesSessionExpiredError,
        validation_error=VolantesValidationError,
    )


def create_volante(payload: dict[str, Any], token: str) -> VolanteDto:
    return create_item(
        token,
        VOLANTES_ENDPOINT,
        VolanteDto,
        payload,
        api_error=VolantesApiError,
        session_error=VolantesSessionExpiredError,
        conflict_error=VolantesConflictError,
        validation_error=VolantesValidationError,
    )
