"""Búsqueda y alta de títulos, cargos, organizaciones y volantes."""

from __future__ import annotations

from typing import Any

from app.api import job_roles_api, organizations_api, titles_api, volantes_api
from app.models.receiver import (
    JobRoleDto,
    OrganizationDto,
    TitleDto,
    VolanteDto,
    present_api_errors,
    validate_job_role_create,
)
from app.services.auth_service import get_access_token
from app.utils.normalizers import (
    normalize_job_role,
    normalize_organization,
    normalize_title,
)

_MIN_SEARCH = 3


class CatalogServiceError(Exception):
    """Error de dominio de un catálogo."""


class CatalogSessionExpiredError(CatalogServiceError):
    """No hay sesión o la API devolvió 401."""


class CatalogConflictError(CatalogServiceError):
    """El registro ya existe."""


class CatalogValidationError(CatalogServiceError):
    """El alta del catálogo no pasó la validación."""

    def __init__(self, errors: list[dict[str, str]]):
        self.errors = errors
        detail = "\n".join(f"{item['campo']}: {item['error']}" for item in errors)
        super().__init__(detail or "Datos inválidos.")


def _required_token() -> str:
    token = get_access_token()
    if not token:
        raise CatalogSessionExpiredError(
            "No hay sesión activa. Inicie sesión de nuevo."
        )
    return token


def _query(text: str) -> str | None:
    query = str(text or "").strip()
    if len(query) < _MIN_SEARCH:
        return None
    return query


def _validation(exc_errors: list[dict[str, str]]) -> CatalogValidationError:
    return CatalogValidationError(present_api_errors(exc_errors))


def search_titles(text: str) -> list[TitleDto]:
    query = _query(normalize_title(text))
    if query is None:
        return []
    token = _required_token()
    try:
        return titles_api.list_titles(token, search=query).items
    except titles_api.TitlesSessionExpiredError as exc:
        raise CatalogSessionExpiredError(str(exc)) from exc
    except titles_api.TitlesValidationError as exc:
        raise _validation(exc.errors) from exc
    except titles_api.TitlesApiError as exc:
        raise CatalogServiceError(str(exc)) from exc


def create_title(abbreviation: str, meaning: str) -> TitleDto:
    return _create(
        {"abbreviation": abbreviation.strip(), "meaning": meaning.strip()},
        titles_api.create_title,
        titles_api.TitlesSessionExpiredError,
        titles_api.TitlesConflictError,
        titles_api.TitlesValidationError,
        titles_api.TitlesApiError,
    )


def search_job_roles(text: str) -> list[JobRoleDto]:
    query = _query(normalize_job_role(text))
    if query is None:
        return []
    token = _required_token()
    try:
        return job_roles_api.list_job_roles(token, search=query).items
    except job_roles_api.JobRolesSessionExpiredError as exc:
        raise CatalogSessionExpiredError(str(exc)) from exc
    except job_roles_api.JobRolesValidationError as exc:
        raise _validation(exc.errors) from exc
    except job_roles_api.JobRolesApiError as exc:
        raise CatalogServiceError(str(exc)) from exc


def create_job_role(abbreviation: str, meaning: str) -> JobRoleDto:
    model, errors = validate_job_role_create(abbreviation, meaning)
    if errors:
        raise CatalogValidationError(errors)
    assert model is not None
    return _create(
        model.model_dump(),
        job_roles_api.create_job_role,
        job_roles_api.JobRolesSessionExpiredError,
        job_roles_api.JobRolesConflictError,
        job_roles_api.JobRolesValidationError,
        job_roles_api.JobRolesApiError,
    )


def search_organizations(text: str, state: str | None = None) -> list[OrganizationDto]:
    query = _query(normalize_organization(text))
    if query is None:
        return []
    token = _required_token()
    try:
        return organizations_api.list_organizations(token, search=query, state=state).items
    except organizations_api.OrganizationsSessionExpiredError as exc:
        raise CatalogSessionExpiredError(str(exc)) from exc
    except organizations_api.OrganizationsValidationError as exc:
        raise _validation(exc.errors) from exc
    except organizations_api.OrganizationsApiError as exc:
        raise CatalogServiceError(str(exc)) from exc


def create_organization(name: str, state: str) -> OrganizationDto:
    return _create(
        {"name": name.strip(), "state": state.strip()},
        organizations_api.create_organization,
        organizations_api.OrganizationsSessionExpiredError,
        organizations_api.OrganizationsConflictError,
        organizations_api.OrganizationsValidationError,
        organizations_api.OrganizationsApiError,
    )


def search_volantes(text: str) -> list[VolanteDto]:
    query = _query(text)
    if query is None:
        return []
    token = _required_token()
    try:
        return volantes_api.list_volantes(token, search=query).items
    except volantes_api.VolantesSessionExpiredError as exc:
        raise CatalogSessionExpiredError(str(exc)) from exc
    except volantes_api.VolantesValidationError as exc:
        raise _validation(exc.errors) from exc
    except volantes_api.VolantesApiError as exc:
        raise CatalogServiceError(str(exc)) from exc


def create_volante(name: str) -> VolanteDto:
    return _create(
        {"name": name.strip()},
        volantes_api.create_volante,
        volantes_api.VolantesSessionExpiredError,
        volantes_api.VolantesConflictError,
        volantes_api.VolantesValidationError,
        volantes_api.VolantesApiError,
    )


def _create(payload: dict[str, Any], fn, session_exc, conflict_exc, validation_exc, api_exc):
    token = _required_token()
    try:
        return fn(payload, token)
    except session_exc as exc:
        raise CatalogSessionExpiredError(str(exc)) from exc
    except conflict_exc as exc:
        raise CatalogConflictError(str(exc)) from exc
    except validation_exc as exc:
        raise _validation(exc.errors) from exc
    except api_exc as exc:
        raise CatalogServiceError(str(exc)) from exc
