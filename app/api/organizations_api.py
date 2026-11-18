"""Transporte HTTP de organizaciones."""

from __future__ import annotations

from typing import Any

from app.api.catalog_http import create_item, list_items, patch_item
from app.config import ORGANIZATIONS_ENDPOINT
from app.models.receiver import OrganizationDto, Paginated


class OrganizationsApiError(Exception):
    """Fallo HTTP de organizaciones."""


class OrganizationsSessionExpiredError(OrganizationsApiError):
    """El backend rechazó el JWT con estado 401."""


class OrganizationsConflictError(OrganizationsApiError):
    """Ya existe esa organización en ese estado."""


class OrganizationsValidationError(OrganizationsApiError):
    """Query o cuerpo inválidos."""

    def __init__(self, errors: list[dict[str, str]]):
        self.errors = errors
        super().__init__("La organización contiene campos inválidos.")


def list_organizations(
    token: str,
    *,
    search: str | None = None,
    state: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> Paginated[OrganizationDto]:
    return list_items(
        token,
        ORGANIZATIONS_ENDPOINT,
        OrganizationDto,
        search=search,
        page=page,
        page_size=page_size,
        extra={"state": state} if state else None,
        api_error=OrganizationsApiError,
        session_error=OrganizationsSessionExpiredError,
        validation_error=OrganizationsValidationError,
    )


def create_organization(payload: dict[str, Any], token: str) -> OrganizationDto:
    return create_item(
        token,
        ORGANIZATIONS_ENDPOINT,
        OrganizationDto,
        payload,
        api_error=OrganizationsApiError,
        session_error=OrganizationsSessionExpiredError,
        conflict_error=OrganizationsConflictError,
        validation_error=OrganizationsValidationError,
    )


def update_organization(
    organization_id: int, payload: dict[str, Any], token: str
) -> OrganizationDto:
    return patch_item(
        token,
        ORGANIZATIONS_ENDPOINT,
        organization_id,
        OrganizationDto,
        payload,
        api_error=OrganizationsApiError,
        session_error=OrganizationsSessionExpiredError,
        conflict_error=OrganizationsConflictError,
        validation_error=OrganizationsValidationError,
    )
