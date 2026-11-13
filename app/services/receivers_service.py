"""Búsqueda y alta de destinatarios."""

from __future__ import annotations

import re
from typing import Any

from app.api import receivers_api
from app.models.receiver import (
    Paginated,
    PositionDto,
    ReceiverDto,
    VolanteDto,
    match_estado,
    present_api_errors,
    validate_receiver,
    validate_receiver_update,
    validate_volante,
)
from app.services.auth_service import get_access_token

_SEARCH_PATTERN = re.compile(r"^[0-9A-Za-zÁÉÍÓÚáéíóúÑñÜü .\-]+$")


class ReceiverServiceError(Exception):
    """Error de dominio del directorio de destinatarios."""


class ReceiverSessionExpiredError(ReceiverServiceError):
    """No hay sesión o la API devolvió 401."""


class ReceiverDuplicateError(ReceiverServiceError):
    """El alta chocó con un destinatario existente."""

    def __init__(self, receiver_id: int, message: str = "El destinatario ya existe"):
        self.receiver_id = receiver_id
        super().__init__(message)


class ReceiverVolanteDuplicateError(ReceiverServiceError):
    """El destinatario ya tiene ese volante."""

    def __init__(self, volante_id: int, message: str = "El destinatario ya tiene ese volante"):
        self.volante_id = volante_id
        super().__init__(message)


class ReceiverValidationError(ReceiverServiceError):
    """Errores acumulados del formulario de destinatario."""

    def __init__(self, errors: list[dict[str, str]]):
        self.errors = errors
        super().__init__("El destinatario contiene campos inválidos.")


def _required_token() -> str:
    token = get_access_token()
    if not token:
        raise ReceiverSessionExpiredError(
            "No hay sesión activa. Inicie sesión de nuevo."
        )
    return token


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _digits(value: Any) -> str:
    return re.sub(r"\D", "", str(value or ""))


def _address_payload(raw: dict[str, Any]) -> dict[str, Any]:
    reference = _clean(raw.get("address_reference"))
    payload = {
        "street": _clean(raw.get("street")),
        "num_street": _clean(raw.get("num_street")),
        "colony": _clean(raw.get("colony")),
        "municipality": _clean(raw.get("municipality")),
        "city": _clean(raw.get("city")),
        "state": _clean(raw.get("state")),
        "postal_code": _clean(raw.get("postal_code")),
        "country": _clean(raw.get("country")) or "MEXICO",
    }
    if reference:
        payload["address_reference"] = reference
    return payload


def _position_payload(form: dict[str, Any]) -> dict[str, Any] | None:
    organization = form.get("organization") or None
    if not isinstance(organization, dict) or not _clean(organization.get("name")):
        return None
    payload: dict[str, Any] = {
        "organization": {
            "name": _clean(organization.get("name")),
            "state": _clean(organization.get("state")),
        }
    }
    role = form.get("job_role")
    if isinstance(role, dict) and _clean(role.get("abbreviation")):
        payload["job_role"] = {
            "abbreviation": _clean(role.get("abbreviation")),
            "meaning": _clean(role.get("meaning")),
        }
    return payload


def build_receiver_payload(form_data: dict[str, Any]) -> dict[str, Any]:
    """Arma el body de ``POST /receivers/`` según el tipo de destinatario.

    PERSONA envía ``title`` y ``full_name``. GOBIERNO y PRIVADA no los envían
    y exigen ``position``. Contacto y volante solo entran si traen valor.
    """
    tipo = _clean(form_data.get("type_entity")).upper()
    payload: dict[str, Any] = {
        "type_entity": tipo,
        "address": _address_payload(form_data.get("address") or {}),
    }
    email = _clean(form_data.get("email"))
    if email:
        payload["email"] = email

    contact = form_data.get("contact")
    if isinstance(contact, dict):
        phone = _digits(contact.get("phone"))
        if phone:
            item: dict[str, Any] = {"phone": phone}
            ext = _digits(contact.get("ext"))
            if ext:
                item["ext"] = ext
            payload["contact"] = item

    volante_name = _clean(form_data.get("volante_name"))
    if volante_name:
        payload["volante"] = {"name": volante_name.upper()}

    if tipo == "PERSONA":
        payload["full_name"] = _clean(form_data.get("full_name"))
        title = form_data.get("title")
        if isinstance(title, dict) and _clean(title.get("abbreviation")):
            payload["title"] = {
                "abbreviation": _clean(title.get("abbreviation")),
                "meaning": _clean(title.get("meaning")),
            }
    position = _position_payload(form_data)
    if position is not None:
        payload["position"] = position
    return payload


def _same_position(form_pos: dict[str, Any] | None, original: PositionDto | None) -> bool:
    if form_pos is None and original is None:
        return True
    if form_pos is None or original is None:
        return False
    form_org = form_pos.get("organization") or {}
    if _clean(form_org.get("name")).upper() != original.organization.name.upper():
        return False
    if match_estado(_clean(form_org.get("state"))) != original.organization.state:
        return False
    form_role = form_pos.get("job_role")
    orig_role = original.job_role
    if form_role is None and orig_role is None:
        return True
    if not isinstance(form_role, dict) or orig_role is None:
        return False
    return (
        _clean(form_role.get("abbreviation")).upper() == orig_role.abbreviation.upper()
        and _clean(form_role.get("meaning")).upper() == orig_role.meaning.upper()
    )


def build_receiver_update_payload(
    form_data: dict[str, Any],
    original: ReceiverDto,
) -> dict[str, Any]:
    """Arma el PATCH de identidad: solo claves que cambiaron.

    No incluye domicilio, contacto ni volante. Tampoco envía ``type_entity``
    si el tipo sigue igual (el formulario lo deja bloqueado).
    """
    payload: dict[str, Any] = {}
    tipo = original.type_entity
    form_type = _clean(form_data.get("type_entity")).upper() or tipo
    if form_type != tipo:
        payload["type_entity"] = form_type

    if tipo == "PERSONA":
        new_name = _clean(form_data.get("full_name"))
        if new_name.upper() != (original.full_name or "").upper():
            payload["full_name"] = new_name
        title = form_data.get("title")
        if isinstance(title, dict) and _clean(title.get("abbreviation")):
            new_title = {
                "abbreviation": _clean(title.get("abbreviation")),
                "meaning": _clean(title.get("meaning")),
            }
            old_abbr = original.title.abbreviation if original.title else ""
            old_meaning = original.title.meaning if original.title else ""
            if (
                new_title["abbreviation"] != old_abbr
                or new_title["meaning"] != old_meaning
            ):
                payload["title"] = new_title

    new_email = _clean(form_data.get("email")) or None
    old_email = original.email or None
    if (new_email or "").lower() != (old_email or "").lower():
        payload["email"] = new_email

    new_position = _position_payload(form_data)
    if not _same_position(new_position, original.position):
        payload["position"] = new_position
    return payload


def search_receivers(
    text: str,
    *,
    type_entity: str | None = None,
    state: str | None = None,
    page: int = 1,
    page_size: int = 10,
    order_by: str = "id",
    direction: str = "asc",
) -> Paginated[ReceiverDto]:
    """Busca por nombre de persona o por organización del puesto."""
    query = _clean(text)
    if len(query) < 3:
        raise ReceiverValidationError(
            [{"campo": "Búsqueda", "error": "Escriba al menos 3 caracteres."}]
        )
    if len(query) > 40 or _SEARCH_PATTERN.fullmatch(query) is None:
        raise ReceiverValidationError(
            [{
                "campo": "Búsqueda",
                "error": "Use hasta 40 letras, números, espacios, puntos o guiones.",
            }]
        )
    token = _required_token()
    try:
        return receivers_api.search_receivers(
            token,
            search=query,
            type_entity=type_entity,
            state=state,
            page=page,
            page_size=page_size,
            order_by=order_by,
            direction=direction,
        )
    except receivers_api.ReceiversSessionExpiredError as exc:
        raise ReceiverSessionExpiredError(str(exc)) from exc
    except receivers_api.ReceiversValidationError as exc:
        raise ReceiverValidationError(present_api_errors(exc.errors)) from exc
    except receivers_api.ReceiversApiError as exc:
        raise ReceiverServiceError(str(exc)) from exc


def create_receiver(form_data: dict[str, Any]) -> ReceiverDto:
    """Valida y crea el destinatario. El body enviado ya va normalizado."""
    payload = build_receiver_payload(form_data)
    model, errors = validate_receiver(payload)
    if errors or model is None:
        raise ReceiverValidationError(errors)
    token = _required_token()
    body = model.model_dump(mode="json", exclude_none=True)
    try:
        return receivers_api.create_receiver(body, token)
    except receivers_api.ReceiverDuplicateError as exc:
        raise ReceiverDuplicateError(exc.receiver_id, str(exc)) from exc
    except receivers_api.ReceiversSessionExpiredError as exc:
        raise ReceiverSessionExpiredError(str(exc)) from exc
    except receivers_api.ReceiversValidationError as exc:
        raise ReceiverValidationError(present_api_errors(exc.errors)) from exc
    except receivers_api.ReceiversApiError as exc:
        raise ReceiverServiceError(str(exc)) from exc


def add_volante(receiver_id: int, name: str) -> VolanteDto:
    """Valida el nombre y lo enlaza al destinatario que ya existe."""
    model, errors = validate_volante(name)
    if errors or model is None:
        raise ReceiverValidationError(errors)
    token = _required_token()
    try:
        return receivers_api.add_volante(
            receiver_id,
            {"name": model.name.upper()},
            token,
        )
    except receivers_api.ReceiverVolanteDuplicateError as exc:
        raise ReceiverVolanteDuplicateError(exc.volante_id, str(exc)) from exc
    except receivers_api.ReceiversSessionExpiredError as exc:
        raise ReceiverSessionExpiredError(str(exc)) from exc
    except receivers_api.ReceiversValidationError as exc:
        raise ReceiverValidationError(present_api_errors(exc.errors)) from exc
    except receivers_api.ReceiversApiError as exc:
        raise ReceiverServiceError(str(exc)) from exc


def update_receiver(
    receiver_id: int,
    form_data: dict[str, Any],
    original: ReceiverDto,
) -> ReceiverDto:
    """Valida y aplica el PATCH de identidad. No toca domicilio ni contacto."""
    payload = build_receiver_update_payload(form_data, original)
    model, errors = validate_receiver_update(payload)
    if errors or model is None:
        raise ReceiverValidationError(errors)
    token = _required_token()
    body = model.model_dump(mode="json", exclude_unset=True)
    try:
        return receivers_api.patch_receiver(receiver_id, body, token)
    except receivers_api.ReceiverDuplicateError as exc:
        raise ReceiverDuplicateError(exc.receiver_id, str(exc)) from exc
    except receivers_api.ReceiversSessionExpiredError as exc:
        raise ReceiverSessionExpiredError(str(exc)) from exc
    except receivers_api.ReceiversValidationError as exc:
        raise ReceiverValidationError(present_api_errors(exc.errors)) from exc
    except receivers_api.ReceiversApiError as exc:
        raise ReceiverServiceError(str(exc)) from exc
