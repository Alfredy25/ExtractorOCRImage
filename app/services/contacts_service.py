"""Alta y edición de un contacto para un destinatario que ya existe."""

from __future__ import annotations

import re
from typing import Any

from app.api import contacts_api
from app.models.receiver import ContactDto, present_api_errors, validate_contact
from app.services.auth_service import get_access_token


class ContactServiceError(Exception):
    """Error de dominio al crear o editar un contacto."""


class ContactSessionExpiredError(ContactServiceError):
    """No hay sesión o la API devolvió 401."""


class ContactDuplicateError(ContactServiceError):
    """Ya hay un contacto con el mismo teléfono y extensión."""


class ContactValidationError(ContactServiceError):
    """Errores acumulados del formulario de contacto."""

    def __init__(self, errors: list[dict[str, str]]):
        self.errors = errors
        super().__init__("El contacto contiene campos inválidos.")


def _required_token() -> str:
    token = get_access_token()
    if not token:
        raise ContactSessionExpiredError(
            "No hay sesión activa. Inicie sesión de nuevo."
        )
    return token


def _digits(value: Any) -> str:
    return re.sub(r"\D", "", str(value or ""))


def build_contact_payload(form_data: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {"phone": _digits(form_data.get("phone"))}
    ext = _digits(form_data.get("ext"))
    if ext:
        payload["ext"] = ext
    return payload


def build_contact_update_payload(
    form_data: dict[str, Any],
    original: ContactDto,
) -> dict[str, Any]:
    """Solo las claves que cambiaron. ``ext: null`` borra la extensión."""
    current = build_contact_payload(form_data)
    changed: dict[str, Any] = {}
    if current["phone"] != _digits(original.phone):
        changed["phone"] = current["phone"]
    new_ext = current.get("ext") or None
    old_ext = _digits(original.ext) or None
    if new_ext != old_ext:
        changed["ext"] = new_ext
    return changed


def create_contact(receiver_id: int, form_data: dict[str, Any]) -> ContactDto:
    """Valida y crea el contacto del destinatario indicado."""
    payload = build_contact_payload(form_data)
    model, errors = validate_contact(payload)
    if errors or model is None:
        raise ContactValidationError(errors)
    token = _required_token()
    try:
        return contacts_api.create_contact(
            receiver_id,
            model.model_dump(mode="json", exclude_none=True),
            token,
        )
    except contacts_api.ContactDuplicateError as exc:
        raise ContactDuplicateError(str(exc)) from exc
    except contacts_api.ContactsSessionExpiredError as exc:
        raise ContactSessionExpiredError(str(exc)) from exc
    except contacts_api.ContactsValidationError as exc:
        raise ContactValidationError(present_api_errors(exc.errors)) from exc
    except contacts_api.ContactsApiError as exc:
        raise ContactServiceError(str(exc)) from exc


def update_contact(
    contact_id: int,
    form_data: dict[str, Any],
    original: ContactDto,
) -> ContactDto:
    """Valida el formulario y envía solo el teléfono o la extensión que cambiaron."""
    payload = build_contact_payload(form_data)
    model, errors = validate_contact(payload)
    if errors or model is None:
        raise ContactValidationError(errors)
    body = build_contact_update_payload(form_data, original)
    if not body:
        return original
    token = _required_token()
    try:
        return contacts_api.patch_contact(contact_id, body, token)
    except contacts_api.ContactDuplicateError as exc:
        raise ContactDuplicateError(str(exc)) from exc
    except contacts_api.ContactsSessionExpiredError as exc:
        raise ContactSessionExpiredError(str(exc)) from exc
    except contacts_api.ContactsValidationError as exc:
        raise ContactValidationError(present_api_errors(exc.errors)) from exc
    except contacts_api.ContactsApiError as exc:
        raise ContactServiceError(str(exc)) from exc
