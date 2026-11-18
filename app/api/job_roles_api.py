"""Transporte HTTP de cargos."""

from __future__ import annotations

from typing import Any

from app.api.catalog_http import create_item, list_items, patch_item
from app.config import JOB_ROLES_ENDPOINT
from app.models.receiver import JobRoleDto, Paginated


class JobRolesApiError(Exception):
    """Fallo HTTP de cargos."""


class JobRolesSessionExpiredError(JobRolesApiError):
    """El backend rechazó el JWT con estado 401."""


class JobRolesConflictError(JobRolesApiError):
    """La abreviatura ya existe."""


class JobRolesValidationError(JobRolesApiError):
    """Query o cuerpo inválidos."""

    def __init__(self, errors: list[dict[str, str]]):
        self.errors = errors
        super().__init__("El cargo contiene campos inválidos.")


def list_job_roles(
    token: str,
    *,
    search: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> Paginated[JobRoleDto]:
    return list_items(
        token,
        JOB_ROLES_ENDPOINT,
        JobRoleDto,
        search=search,
        page=page,
        page_size=page_size,
        api_error=JobRolesApiError,
        session_error=JobRolesSessionExpiredError,
        validation_error=JobRolesValidationError,
    )


def create_job_role(payload: dict[str, Any], token: str) -> JobRoleDto:
    return create_item(
        token,
        JOB_ROLES_ENDPOINT,
        JobRoleDto,
        payload,
        api_error=JobRolesApiError,
        session_error=JobRolesSessionExpiredError,
        conflict_error=JobRolesConflictError,
        validation_error=JobRolesValidationError,
    )


def update_job_role(job_id: int, payload: dict[str, Any], token: str) -> JobRoleDto:
    return patch_item(
        token,
        JOB_ROLES_ENDPOINT,
        job_id,
        JobRoleDto,
        payload,
        api_error=JobRolesApiError,
        session_error=JobRolesSessionExpiredError,
        conflict_error=JobRolesConflictError,
        validation_error=JobRolesValidationError,
    )
