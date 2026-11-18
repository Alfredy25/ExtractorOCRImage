"""Modelos de destinatarios, catálogos y validación del alta."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, Literal, TypeVar

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

TypeEntity = Literal["PERSONA", "GOBIERNO", "PRIVADA"]

ESTADOS_MX: tuple[str, ...] = (
    "AGUASCALIENTES",
    "BAJA CALIFORNIA",
    "BAJA CALIFORNIA SUR",
    "CAMPECHE",
    "CHIAPAS",
    "CHIHUAHUA",
    "CIUDAD DE MEXICO",
    "COAHUILA",
    "COLIMA",
    "DURANGO",
    "ESTADO DE MEXICO",
    "GUANAJUATO",
    "GUERRERO",
    "HIDALGO",
    "JALISCO",
    "MICHOACAN",
    "MORELOS",
    "NAYARIT",
    "NUEVO LEON",
    "OAXACA",
    "PUEBLA",
    "QUERETARO",
    "QUINTANA ROO",
    "SAN LUIS POTOSI",
    "SINALOA",
    "SONORA",
    "TABASCO",
    "TAMAULIPAS",
    "TLAXCALA",
    "VERACRUZ",
    "YUCATAN",
    "ZACATECAS",
)

_STATE_ALIASES = {
    "CDMX": "CIUDAD DE MEXICO",
    "DISTRITO FEDERAL": "CIUDAD DE MEXICO",
    "DF": "CIUDAD DE MEXICO",
    "EDOMEX": "ESTADO DE MEXICO",
    "MEXICO D.F.": "CIUDAD DE MEXICO",
    "MEXICO DF": "CIUDAD DE MEXICO",
}

_ACCENTS = str.maketrans("ÁÉÍÓÚÜ", "AEIOUU")

T = TypeVar("T")


def strip_accents(value: str) -> str:
    return value.translate(_ACCENTS)


def match_estado(value: str) -> str | None:
    """Devuelve el estado del catálogo o ``None`` si no coincide."""
    text = strip_accents(str(value or "").strip().upper())
    text = _STATE_ALIASES.get(text, text)
    if text in ESTADOS_MX:
        return text
    return None


class _Audit(BaseModel):
    created_at: datetime
    updated_at: datetime
    created_by: int | None = None
    updated_by: int | None = None


class TitleDto(_Audit):
    id: int
    abbreviation: str
    meaning: str


class JobRoleDto(_Audit):
    id: int
    abbreviation: str
    meaning: str


class OrganizationDto(_Audit):
    id: int
    name: str
    state: str


class VolanteDto(_Audit):
    id: int
    name: str


class AddressDto(_Audit):
    id: int
    street: str
    num_street: str
    colony: str
    municipality: str
    city: str
    state: str
    postal_code: str
    country: str
    address_reference: str | None = None
    receiver_id: int


class ContactDto(_Audit):
    id: int
    phone: str
    ext: str | None = None
    id_destinatario: int


class PositionDto(_Audit):
    id: int
    job_role: JobRoleDto | None = None
    organization: OrganizationDto


class ReceiverDto(_Audit):
    id: int
    type_entity: TypeEntity
    title: TitleDto | None = None
    full_name: str | None = None
    email: str | None = None
    position: PositionDto | None = None
    addresses: list[AddressDto] = Field(default_factory=list)
    contacts: list[ContactDto] = Field(default_factory=list)
    volantes: list[VolanteDto] = Field(default_factory=list)


class Paginated(BaseModel, Generic[T]):
    """Página común de los listados del directorio."""

    page: int
    page_size: int
    total: int
    total_pages: int
    has_prev: bool = False
    has_next: bool = False
    order_by: str | None = None
    direction: str | None = None
    search: str | None = None
    state: str | None = None
    items: list[T]


def receiver_display_name(receiver: ReceiverDto) -> str:
    """Nombre visible: persona con título, o la organización si es institución."""
    if receiver.type_entity == "PERSONA":
        prefix = f"{receiver.title.abbreviation} " if receiver.title else ""
        return f"{prefix}{receiver.full_name or ''}".strip() or f"Destinatario {receiver.id}"
    if receiver.position is not None:
        return receiver.position.organization.name
    return f"Destinatario {receiver.id}"


def contact_display_line(contact: ContactDto) -> str:
    """Teléfono visible, con extensión si existe."""
    phone = (contact.phone or "").strip()
    if contact.ext:
        return f"{phone} ext. {contact.ext}"
    return phone or "Sin teléfono"


def receiver_position_line(receiver: ReceiverDto) -> str:
    if receiver.position is None:
        return ""
    role = receiver.position.job_role.meaning if receiver.position.job_role else ""
    org = receiver.position.organization.name
    if role and org:
        return f"{role} en {org}"
    return role or org


NAME_RECEIVER_LIMIT = 80

# El servidor asigna uno de estos cuando el destinatario no tiene un cargo real.
_PLACEHOLDER_ROLE_ABBREVIATIONS = frozenset({
    "SIN CARGO",
    "INSTITUCIONAL GOBIERNO",
    "INSTITUCIONAL PRIVADO",
})


def _shipment_role(abbreviation: str | None) -> str:
    """Abreviatura de cargo que sí se manda en ``name_receiver``."""
    role = (abbreviation or "").strip()
    if role.upper() in _PLACEHOLDER_ROLE_ABBREVIATIONS:
        return ""
    return role


def persona_shipment_name(
    title_abbreviation: str | None = None,
    full_name: str | None = None,
    role_abbreviation: str | None = None,
    organization_name: str | None = None,
) -> str:
    """Título, nombre, cargo y organización, recortado al límite de ``name_receiver``.

    Forma: ``M. EN A.P. SONIA ISELA DÍAZ / CONT. GRAL. GUB. EN SECRETARÍA``.
    ``EN`` solo aparece cuando hay abreviatura de cargo y nombre de organización.
    ``SIN CARGO``, ``INSTITUCIONAL GOBIERNO`` e ``INSTITUCIONAL PRIVADO`` no se
    concatenan: queda la organización sola después de la diagonal.
    """
    identity = " ".join(
        part.strip()
        for part in (title_abbreviation or "", full_name or "")
        if part and part.strip()
    )
    role = _shipment_role(role_abbreviation)
    organization = (organization_name or "").strip()
    if role and organization:
        position = f"{role} EN {organization}"
    else:
        position = role or organization
    if identity and position:
        text = f"{identity} {position}"
    else:
        text = identity or position
    return text[:NAME_RECEIVER_LIMIT]


def institution_shipment_name(
    role_abbreviation: str | None = None,
    organization_name: str | None = None,
    organization_state: str | None = None,
) -> str:
    """Abreviatura del cargo, organización y su estado. Límite de ``name_receiver``.

    Forma: ``PDTE. MPAL. MPIO. DE EL GRULLO JALISCO``. Sirve para GOBIERNO y PRIVADA.
    Los cargos fijos ``SIN CARGO``, ``INSTITUCIONAL GOBIERNO`` e
    ``INSTITUCIONAL PRIVADO`` no se concatenan.
    """
    organization = " ".join(
        part.strip()
        for part in (organization_name or "", organization_state or "")
        if part and part.strip()
    )
    role = _shipment_role(role_abbreviation)
    if role and organization:
        text = f"{role} {organization}"
    else:
        text = role or organization
    return text[:NAME_RECEIVER_LIMIT]


def shipment_receiver_name(receiver: ReceiverDto) -> str:
    """Texto de ``name_receiver`` según el tipo de destinatario."""
    if receiver.type_entity == "PERSONA":
        role = ""
        organization = ""
        if receiver.position is not None:
            organization = receiver.position.organization.name
            if receiver.position.job_role is not None:
                role = receiver.position.job_role.abbreviation
        title = receiver.title.abbreviation if receiver.title else ""
        return persona_shipment_name(title, receiver.full_name, role, organization)
    role = ""
    organization = ""
    state = ""
    if receiver.position is not None:
        organization = receiver.position.organization.name
        state = receiver.position.organization.state
        if receiver.position.job_role is not None:
            role = receiver.position.job_role.abbreviation
    return institution_shipment_name(role, organization, state)


class TitleInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    abbreviation: str = Field(..., min_length=2, max_length=60)
    meaning: str = Field(..., min_length=3, max_length=150)


_JOB_ROLE_FIELD_PATTERN = r"^[a-zA-Z0-9áéíóúÁÉÍÓÚñÑ. ]+$"


class JobRoleInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    abbreviation: str = Field(
        ...,
        min_length=2,
        max_length=60,
        pattern=_JOB_ROLE_FIELD_PATTERN,
    )
    meaning: str = Field(
        ...,
        min_length=3,
        max_length=150,
        pattern=_JOB_ROLE_FIELD_PATTERN,
    )


class OrganizationInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(..., min_length=3, max_length=180)
    state: str

    @field_validator("state", mode="before")
    @classmethod
    def _state(cls, value: Any) -> str:
        matched = match_estado(str(value or ""))
        if matched is None:
            raise ValueError("Debe ser uno de los 32 estados")
        return matched


class PositionInput(BaseModel):
    job_role: JobRoleInput | None = None
    organization: OrganizationInput


class AddressInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    street: str = Field(..., min_length=3, max_length=80)
    num_street: str = Field(..., min_length=1, max_length=15)
    colony: str = Field(..., min_length=3, max_length=60)
    municipality: str = Field(..., min_length=3, max_length=60)
    city: str = Field(..., min_length=3, max_length=60)
    state: str
    postal_code: str = Field(..., min_length=4, max_length=5)
    country: str = Field(..., min_length=3, max_length=50)
    address_reference: str | None = Field(default=None, max_length=50)

    @field_validator("state", mode="before")
    @classmethod
    def _state(cls, value: Any) -> str:
        matched = match_estado(str(value or ""))
        if matched is None:
            raise ValueError("Debe ser uno de los 32 estados")
        return matched

    @field_validator("address_reference", mode="before")
    @classmethod
    def _reference(cls, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None


class ContactInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    phone: str = Field(..., min_length=8, max_length=10, pattern=r"^\d+$")
    ext: str | None = Field(default=None, max_length=5, pattern=r"^\d+$")

    @field_validator("ext", mode="before")
    @classmethod
    def _ext(cls, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None


class VolanteInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(..., min_length=18, max_length=35)


class ReceiverCreateRequest(BaseModel):
    """Cuerpo de ``POST /receivers/`` con las reglas de tipo."""

    model_config = ConfigDict(str_strip_whitespace=True)

    type_entity: TypeEntity
    title: TitleInput | None = None
    full_name: str | None = Field(default=None, min_length=5, max_length=70)
    email: EmailStr | None = None
    position: PositionInput | None = None
    address: AddressInput
    contact: ContactInput | None = None
    volante: VolanteInput | None = None

    @field_validator("full_name", mode="before")
    @classmethod
    def _full_name(cls, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip().upper()
        return text or None

    @field_validator("email", mode="before")
    @classmethod
    def _email(cls, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @field_validator("email")
    @classmethod
    def _email_len(cls, value: EmailStr | None) -> EmailStr | None:
        if value is not None and len(str(value)) > 80:
            raise ValueError("Debe tener máximo 80 caracteres")
        return value

    @model_validator(mode="after")
    def _type_rules(self) -> ReceiverCreateRequest:
        if self.type_entity == "PERSONA":
            if not self.full_name:
                raise ValueError("El nombre es requerido para PERSONA")
            if self.title is None:
                raise ValueError("El título es requerido para PERSONA")
        else:
            if self.full_name or self.title is not None:
                raise ValueError(
                    "El nombre y el título no son permitidos para GOBIERNO o PRIVADA"
                )
            if self.position is None:
                raise ValueError("El puesto es requerido para GOBIERNO o PRIVADA")
        return self


class ReceiverUpdateRequest(BaseModel):
    """Cuerpo de ``PATCH /receivers/{id}``. Solo se validan las claves enviadas."""

    model_config = ConfigDict(str_strip_whitespace=True)

    full_name: str | None = Field(default=None, min_length=5, max_length=70)
    email: EmailStr | None = None
    title: TitleInput | None = None
    position: PositionInput | None = None
    type_entity: TypeEntity | None = None

    @field_validator("full_name", mode="before")
    @classmethod
    def _full_name(cls, value: Any) -> str:
        if value is None:
            raise ValueError("El nombre no puede ser nulo")
        text = str(value).strip().upper()
        if not text:
            raise ValueError("El nombre no puede ser nulo")
        return text

    @field_validator("email", mode="before")
    @classmethod
    def _email(cls, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @field_validator("email")
    @classmethod
    def _email_len(cls, value: EmailStr | None) -> EmailStr | None:
        if value is not None and len(str(value)) > 80:
            raise ValueError("Debe tener máximo 80 caracteres")
        return value

    @field_validator("title", mode="before")
    @classmethod
    def _title(cls, value: Any) -> Any:
        if value is None:
            raise ValueError("El título no puede ser nulo")
        return value

    @field_validator("type_entity", mode="before")
    @classmethod
    def _type(cls, value: Any) -> Any:
        if value is None:
            raise ValueError("El tipo no puede ser nulo")
        return value


_FIELD_LABELS = {
    "type_entity": "Tipo",
    "full_name": "Nombre completo",
    "email": "Correo",
    "title": "Título",
    "title.abbreviation": "Abreviatura del título",
    "title.meaning": "Significado del título",
    "position": "Puesto",
    "position.organization": "Organización",
    "position.organization.name": "Organización",
    "position.organization.state": "Estado de la organización",
    "position.job_role.abbreviation": "Abreviatura del cargo",
    "position.job_role.meaning": "Cargo",
    "address": "Domicilio",
    "address.street": "Calle",
    "address.num_street": "Número",
    "address.colony": "Colonia",
    "address.municipality": "Municipio",
    "address.city": "Ciudad",
    "address.state": "Estado",
    "address.postal_code": "Código postal",
    "address.country": "País",
    "address.address_reference": "Referencia",
    "contact.phone": "Teléfono",
    "contact.ext": "Extensión",
    "phone": "Teléfono",
    "ext": "Extensión",
    "volante.name": "Volante",
    "name": "Volante",
    "street": "Calle",
    "num_street": "Número",
    "colony": "Colonia",
    "municipality": "Municipio",
    "city": "Ciudad",
    "state": "Estado",
    "postal_code": "Código postal",
    "country": "País",
    "address_reference": "Referencia",
    "Destinatario": "Destinatario",
}

_LENGTH_MESSAGES = {
    "full_name": "Debe tener entre 5 y 70 caracteres",
    "title.abbreviation": "Debe tener entre 2 y 60 caracteres",
    "title.meaning": "Debe tener entre 3 y 150 caracteres",
    "position.organization.name": "Debe tener entre 3 y 180 caracteres",
    "position.job_role.abbreviation": "Debe tener entre 2 y 60 caracteres",
    "position.job_role.meaning": "Debe tener entre 3 y 150 caracteres",
    "address.street": "Debe tener entre 3 y 80 caracteres",
    "address.num_street": "Debe tener entre 1 y 15 caracteres",
    "address.colony": "Debe tener entre 3 y 60 caracteres",
    "address.municipality": "Debe tener entre 3 y 60 caracteres",
    "address.city": "Debe tener entre 3 y 60 caracteres",
    "address.postal_code": "Debe tener entre 4 y 5 caracteres",
    "address.country": "Debe tener entre 3 y 50 caracteres",
    "address.address_reference": "Debe tener máximo 50 caracteres",
    "contact.phone": "Debe tener entre 8 y 10 dígitos",
    "contact.ext": "Debe tener máximo 5 dígitos",
    "phone": "Debe tener entre 8 y 10 dígitos",
    "ext": "Debe tener máximo 5 dígitos",
    "volante.name": "Debe tener entre 18 y 35 caracteres",
    "name": "Debe tener entre 18 y 35 caracteres",
    "street": "Debe tener entre 3 y 80 caracteres",
    "num_street": "Debe tener entre 1 y 15 caracteres",
    "colony": "Debe tener entre 3 y 60 caracteres",
    "municipality": "Debe tener entre 3 y 60 caracteres",
    "city": "Debe tener entre 3 y 60 caracteres",
    "postal_code": "Debe tener entre 4 y 5 caracteres",
    "country": "Debe tener entre 3 y 50 caracteres",
    "address_reference": "Debe tener máximo 50 caracteres",
}

_GENERIC_FIELDS = {"Destinatario", "body", "receiver"}


def _loc(detail: dict[str, Any]) -> str:
    parts = [str(part) for part in detail.get("loc", ()) if str(part) != "__root__"]
    return ".".join(parts) if parts else "Destinatario"


def _message(field: str, detail: dict[str, Any]) -> str:
    error_type = str(detail.get("type", ""))
    if error_type in {"string_too_short", "string_too_long"}:
        return _LENGTH_MESSAGES.get(field, "Longitud inválida")
    if error_type == "string_pattern_mismatch":
        if field.endswith("phone") or field.endswith("ext"):
            return "Debe contener únicamente dígitos"
        return "Formato inválido"
    if error_type == "missing":
        return "Campo obligatorio"
    if error_type in {"value_error", "literal_error"}:
        text = str(detail.get("msg", "Valor inválido"))
        prefix = "Value error, "
        return text[len(prefix):] if text.startswith(prefix) else text
    return str(detail.get("msg", "Valor inválido"))


def _from_validation(exc: ValidationError) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    for detail in exc.errors():
        field = _loc(detail)
        errors.append(
            {
                "campo": _FIELD_LABELS.get(field, field),
                "error": _message(field, detail),
            }
        )
    return errors


def _type_rule_errors(data: dict[str, Any]) -> list[dict[str, str]]:
    tipo = data.get("type_entity")
    errors: list[dict[str, str]] = []
    if tipo == "PERSONA":
        if not str(data.get("full_name") or "").strip():
            errors.append(
                {"campo": "Nombre completo", "error": "El nombre es requerido para PERSONA"}
            )
        if not data.get("title"):
            errors.append(
                {"campo": "Título", "error": "El título es requerido para PERSONA"}
            )
        return errors
    if tipo in {"GOBIERNO", "PRIVADA"}:
        if data.get("full_name") or data.get("title"):
            errors.append(
                {
                    "campo": "Tipo",
                    "error": "El nombre y el título no son permitidos para GOBIERNO o PRIVADA",
                }
            )
        if not data.get("position"):
            errors.append(
                {
                    "campo": "Puesto",
                    "error": "El puesto es requerido para GOBIERNO o PRIVADA",
                }
            )
        return errors
    errors.append(
        {"campo": "Tipo", "error": "El tipo debe ser PERSONA, GOBIERNO o PRIVADA"}
    )
    return errors


def _dedupe(errors: list[dict[str, str]]) -> list[dict[str, str]]:
    kept: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    messages = set()
    for err in errors:
        key = (err["campo"], err["error"])
        if key in seen:
            continue
        if err["campo"] in _GENERIC_FIELDS and err["error"] in messages:
            continue
        seen.add(key)
        messages.add(err["error"])
        kept.append(err)
    return kept


def present_api_errors(errors: list[dict[str, str]]) -> list[dict[str, str]]:
    """Traduce un 422 del servidor al formato ``campo`` / ``error``."""
    presented: list[dict[str, str]] = []
    for item in errors:
        field = str(item.get("field") or "body")
        presented.append(
            {
                "campo": _FIELD_LABELS.get(field, field),
                "error": str(item.get("message") or "Valor inválido"),
            }
        )
    return presented


def validate_job_role_create(
    abbreviation: str,
    meaning: str,
) -> tuple[JobRoleInput | None, list[dict[str, str]]]:
    """Valida abreviatura y significado antes de ``POST /job-roles/``."""
    try:
        model = JobRoleInput.model_validate({
            "abbreviation": str(abbreviation or "").strip(),
            "meaning": str(meaning or "").strip(),
        })
    except ValidationError as exc:
        return None, _dedupe(_from_validation(exc))
    return model, []


def validate_address(
    data: dict[str, Any],
) -> tuple[AddressInput | None, list[dict[str, str]]]:
    """Valida un domicilio y acumula los errores de campo."""
    try:
        return AddressInput.model_validate(data), []
    except ValidationError as exc:
        return None, _dedupe(_from_validation(exc))


def validate_receiver(
    data: dict[str, Any],
) -> tuple[ReceiverCreateRequest | None, list[dict[str, str]]]:
    """Valida el alta de destinatario, incluidas las reglas por tipo."""
    errors = _type_rule_errors(data)
    try:
        model = ReceiverCreateRequest.model_validate(data)
    except ValidationError as exc:
        errors.extend(_from_validation(exc))
        return None, _dedupe(errors)
    errors = _dedupe(errors)
    if errors:
        return None, errors
    return model, []


def validate_receiver_update(
    data: dict[str, Any],
) -> tuple[ReceiverUpdateRequest | None, list[dict[str, str]]]:
    """Valida el PATCH de identidad. Un cuerpo vacío es válido."""
    if not data:
        return ReceiverUpdateRequest(), []
    try:
        return ReceiverUpdateRequest.model_validate(data), []
    except ValidationError as exc:
        return None, _dedupe(_from_validation(exc))


def validate_volante(
    name: str,
) -> tuple[VolanteInput | None, list[dict[str, str]]]:
    """Valida el nombre antes de enlazar un volante a un destinatario."""
    try:
        return VolanteInput.model_validate({"name": name}), []
    except ValidationError as exc:
        return None, _dedupe(_from_validation(exc))


def validate_contact(
    data: dict[str, Any],
) -> tuple[ContactInput | None, list[dict[str, str]]]:
    """Valida teléfono y extensión antes de ``POST /contacts/``."""
    try:
        return ContactInput.model_validate(data), []
    except ValidationError as exc:
        return None, _dedupe(_from_validation(exc))
