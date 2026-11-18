"""Transporte HTTP de títulos."""

from __future__ import annotations

from typing import Any

from app.api.catalog_http import create_item, list_items, patch_item
from app.config import TITLES_ENDPOINT
from app.models.receiver import Paginated, TitleDto


class TitlesApiError(Exception):
    """Fallo HTTP de títulos."""


class TitlesSessionExpiredError(TitlesApiError):
    """El backend rechazó el JWT con estado 401."""


class TitlesConflictError(TitlesApiError):
    """La abreviatura ya existe."""


class TitlesValidationError(TitlesApiError):
    """Query o cuerpo inválidos."""

    def __init__(self, errors: list[dict[str, str]]):
        self.errors = errors
        super().__init__("El título contiene campos inválidos.")


def list_titles(
    token: str,
    *,
    search: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> Paginated[TitleDto]:
    return list_items(
        token,
        TITLES_ENDPOINT,
        TitleDto,
        search=search,
        page=page,
        page_size=page_size,
        api_error=TitlesApiError,
        session_error=TitlesSessionExpiredError,
        validation_error=TitlesValidationError,
    )


def create_title(payload: dict[str, Any], token: str) -> TitleDto:
    return create_item(
        token,
        TITLES_ENDPOINT,
        TitleDto,
        payload,
        api_error=TitlesApiError,
        session_error=TitlesSessionExpiredError,
        conflict_error=TitlesConflictError,
        validation_error=TitlesValidationError,
    )


def update_title(title_id: int, payload: dict[str, Any], token: str) -> TitleDto:
    return patch_item(
        token,
        TITLES_ENDPOINT,
        title_id,
        TitleDto,
        payload,
        api_error=TitlesApiError,
        session_error=TitlesSessionExpiredError,
        conflict_error=TitlesConflictError,
        validation_error=TitlesValidationError,
    )
