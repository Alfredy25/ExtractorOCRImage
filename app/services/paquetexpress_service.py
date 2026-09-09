"""Fachada de negocio para consulta de coberturas y creación de envíos PX."""

from __future__ import annotations
import re

from decimal import Decimal
from typing import Any

from app.api.coverages_api import (
    CoverageNotFoundError,
    CoveragesApiError,
    CoveragesSessionExpiredError,
    get_coverages,
)
from app.api.shipments_api import (
    ShipmentsApiError,
    ShipmentsSessionExpiredError,
    create_shipment as api_create_shipment,
    list_by_date_range,
    update_shipment as api_update_shipment,
)
from datetime import datetime
from app.models.shipping import (
    CoverageItem,
    ShippingDto,
    ShippingFieldError,
    ShippingRequest,
    validate_shipping,
)
from app.services.auth_service import get_access_token


class PaquetexpressServiceError(Exception):
    """Error de dominio del flujo Paquetexpress."""


class PaquetexpressSessionExpiredError(PaquetexpressServiceError):
    """No hay sesión o la API devolvió 401."""


class PaquetexpressCoverageNotFoundError(PaquetexpressServiceError):
    """No se encontró cobertura para el código postal."""


class PaquetexpressValidationError(PaquetexpressServiceError):
    """Errores de validación acumulados para crear envío."""

    def __init__(self, errors: list[ShippingFieldError]):
        self.errors = errors
        super().__init__("El envío contiene campos inválidos.")


def _required_token() -> str:
    token = get_access_token()
    if not token:
        raise PaquetexpressSessionExpiredError(
            "No hay sesión activa. Inicie sesión de nuevo."
        )
    return token


def _first_non_empty(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _join_non_empty(*values: Any, sep: str = " ") -> str:
    parts = [str(value or "").strip() for value in values]
    return sep.join(part for part in parts if part)


def _to_optional_string(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _to_coverage_item(item: dict[str, Any]) -> CoverageItem | None:
    try:
        return CoverageItem.model_validate(item)
    except Exception:
        return None


def get_coverages_for_postal_code(postal_code: str) -> list[CoverageItem]:
    """Obtiene coberturas tipadas para un código postal."""
    token = _required_token()
    try:
        raw = get_coverages(postal_code, token)
    except CoverageNotFoundError as exc:
        raise PaquetexpressCoverageNotFoundError(str(exc)) from exc
    except CoveragesSessionExpiredError as exc:
        raise PaquetexpressSessionExpiredError(str(exc)) from exc
    except CoveragesApiError as exc:
        raise PaquetexpressServiceError(str(exc)) from exc

    items = [_to_coverage_item(item) for item in raw]
    valid_items = [item for item in items if item is not None]
    if not valid_items:
        raise PaquetexpressServiceError(
            "La API devolvió coberturas con formato no reconocido."
        )
    return valid_items


def build_shipment_draft(ocr_form_data: dict[str, Any], coverage: CoverageItem) -> dict[str, Any]:
    """Arma los valores iniciales del formulario de envío desde OCR + cobertura."""
    campos = ocr_form_data.get("campos") or {}
    return {
        "name_receiver": _join_non_empty(
            campos.get("nombre_titulo"),
            campos.get("cargo_dependencia"),
        ),
        "rfc": "XAXX-010101-000",
        "country": "MEXICO",
        "state": coverage.state,
        "city": coverage.city,
        "colony": coverage.colony,
        "street": str(campos.get("direccion") or "").strip(),
        "num_street": "",
        "postal_code": coverage.postal_code,
        "email": "notificaciones@feuh.com.mx",
        "phone": _first_non_empty(campos.get("contacto"), "55 7586 8462"),
        "address_reference": str(campos.get("indicaciones") or "").strip(),
        "quantity": "1",
        "package_code": "1",
        "content": "DOCUMENTOS LEGALES",
        "comments": "ENTREGAR EN OFICIALIA DE PARTES O RECEPCION EN UN HORARIO DE 09:00 A 14:00 HRS.",
        "weight": "0.5",
        "length": "30",
        "width": "24",
        "height": "1",
        "coverage_type": coverage.coverage_type,
    }


def _normalize_shipment_form(data: dict[str, Any]) -> dict[str, Any]:
    normalized = {
        "name_receiver": str(data.get("name_receiver") or "").strip(),
        "rfc": str(data.get("rfc") or "").strip(),
        "country": str(data.get("country") or "").strip(),
        "state": str(data.get("state") or "").strip(),
        "city": str(data.get("city") or "").strip(),
        "colony": str(data.get("colony") or "").strip(),
        "street": str(data.get("street") or "").strip(),
        "num_street": str(data.get("num_street") or "").strip(),
        "postal_code": str(data.get("postal_code") or "").strip(),
        "email": _to_optional_string(data.get("email")),
        "phone": _to_optional_string(data.get("phone")),
        "address_reference": _to_optional_string(data.get("address_reference")),
        "quantity": data.get("quantity"),
        "package_code": data.get("package_code"),
        "content": str(data.get("content") or "").strip(),
        "comments": _to_optional_string(data.get("comments")),
        "weight": data.get("weight"),
        "length": data.get("length"),
        "width": data.get("width"),
        "height": data.get("height"),
        "coverage_type": str(data.get("coverage_type") or "").strip(),
    }
    return normalized


def validate_shipment_form(data: dict[str, Any]) -> list[ShippingFieldError]:
    """Valida acumulativamente todos los campos del formulario de envío."""
    normalized = _normalize_shipment_form(data)
    _, errors = validate_shipping(normalized)
    return errors


def _parse_decimal_for_payload(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value).strip())


def _payload_from_shipping_request(model: ShippingRequest) -> dict[str, Any]:
    payload = model.model_dump(exclude_none=True)
    payload["quantity"] = int(payload["quantity"])
    payload["package_code"] = int(payload["package_code"])
    payload["weight"] = _parse_decimal_for_payload(payload["weight"])
    payload["length"] = _parse_decimal_for_payload(payload["length"])
    payload["width"] = _parse_decimal_for_payload(payload["width"])
    payload["height"] = _parse_decimal_for_payload(payload["height"])
    payload["weight"] = f"{payload['weight']:.2f}"
    payload["length"] = f"{payload['length']:.2f}"
    payload["width"] = f"{payload['width']:.2f}"
    payload["height"] = f"{payload['height']:.2f}"
    return payload


def create_shipment(data: dict[str, Any]) -> dict[str, Any]:
    """Valida y crea un envío Paquetexpress."""
    normalized = _normalize_shipment_form(data)
    model, errors = validate_shipping(normalized)
    if errors:
        raise PaquetexpressValidationError(errors)
    assert model is not None

    token = _required_token()
    payload = _payload_from_shipping_request(model)

    try:
        return api_create_shipment(payload, token)
    except ShipmentsSessionExpiredError as exc:
        raise PaquetexpressSessionExpiredError(str(exc)) from exc
    except ShipmentsApiError as exc:
        raise PaquetexpressServiceError(str(exc)) from exc


def update_shipment(id_shipping: int, data: dict[str, Any]) -> ShippingDto:
    """Valida y actualiza un envío Paquetexpress."""
    normalized = _normalize_shipment_form(data)
    model, errors = validate_shipping(normalized)
    if errors:
        raise PaquetexpressValidationError(errors)
    assert model is not None

    token = _required_token()
    payload = _payload_from_shipping_request(model)

    try:
        return api_update_shipment(id_shipping, payload, token)
    except ShipmentsSessionExpiredError as exc:
        raise PaquetexpressSessionExpiredError(str(exc)) from exc
    except ShipmentsApiError as exc:
        raise PaquetexpressServiceError(str(exc)) from exc

def list_shipments_by_date_range(
    desde: datetime,
    hasta: datetime,
    my_shipments: bool = False,
) -> list[ShippingDto]:
    """Lista los envíos de fechas entre desde y hasta.

    ``my_shipments=True`` limita el resultado a los del usuario en sesión.
    """
    token = _required_token()
    try:
        return list_by_date_range(desde, hasta, token, my_shipments=my_shipments)
    except ShipmentsSessionExpiredError as exc:
        raise PaquetexpressSessionExpiredError(str(exc)) from exc
    except ShipmentsApiError as exc:
        raise PaquetexpressServiceError(str(exc)) from exc

replacements_vocales = {
    "Á": "A",
    "É": "E",
    "Í": "I",
    "Ó": "O",
    "Ú": "U",
    "?": "Ñ",
}

replacements_especiales = {
    "\\": "",
    ":": "",
    "[": "",
    "]": "",
    "#": "",
    "°": "",
    "-": " ",
    '"': "",
    ",": "",
    "!": "",
    "¿": "",
    "¡": "",
    "“": "",
    "”": "",
}


replacements_frases_largas = {
    "SECRETARIA DE ADMINISTRACION TRIBUTARIA": "S.A.T.",
    "SECRETARIA DE CONTRALORIA GENERAL": "S.C.E.",
    "ORGANO INTERNO DE CONTROL": "O.I.C.",
    "ORGANO DE CONTROL INTERNO": "O.I.C.",
    "CONTRALORIA GENERAL DEL ESTADO": "C.G.E.",
    "BAJA CALIFORNIA SUR": "B.C.S.",
    "SAN LUIS POTOSI": "S.L.P.",
}

replacements_cargos = {
    "ADMINISTRADORA": "ADMIN.",
    "ADMINISTRADOR": "ADMIN.",
    "ADMINISTRACION": "ADMON.",
    "PRESIDENTA": "PDTA.",
    "PRESIDENTE": "PDTE.",
    "DIRECTORA": "DIR.A",
    "DIRECTOR": "DIR.",
    "SECRETARIA": "SECRET.A",
    "SECRETARIO": "SEC.",
    "GOBERNADOR": "GOB.",
    "UNIVERSIDAD": "UNI",
    "AUTONOMA": "AUT.",
    "MAESTRA": "MTRA.",
    "MAESTRO": "MTRO.",
    "PROFESORA": "PROFA.",
    "PROFESOR": "PROF.",
    "DIPUTADA": "DIP.",
    "DIPUTADO": "DIP.",
    "SENADORA": "SEN.",
    "SENADOR": "SEN.",
    "DOCTORA": "DRA.",
    "DOCTOR": "DR.",
    "TITULAR": "TIT.",
    "GENERAL": "GRAL.",
    "CONTADOR PUBLICO": "C.P.",
    "CIUDADANO": "C.",
    "CIUDAD": "C.D."
}

replacements_direcciones = {
    "AVENIDA": "AV.",
    "BOULEVARD": "BLVD.",
    "CARRETERA": "CARR.",
    "CALLE": "C.",
    "EDIFICIO": "EDIF."
}

def _replace_whole_words(text: str, mapping: dict[str, str]) -> str:
    """Reemplaza solo palabras completas usando un diccionario origen → destino.

    Parameters
    ----------
    text:
        Cadena ya en mayúsculas donde se buscan las claves.
    mapping:
        Diccionario ``{"PALABRA": "ABREV."}``. Las claves más largas
        tienen prioridad para no recortar un término dentro de otro
        (``ADMINISTRADORA`` antes que ``ADMINISTRADOR``).

    Returns
    -------
    str
        El mismo ``text`` si viene vacío o el ``mapping`` está vacío;
        si no, el texto con cada coincidencia sustituida por su valor.
    """
    if not text or not mapping:
        return text

    # \b = límite de palabra (espacio, inicio/fin o puntuación).
    # (?:A|B|C) = una de las claves, sin capturar grupo extra.
    # re.escape evita que caracteres como "." se lean como regex.
    # key=len, reverse=True pone primero las frases más largas.
    pattern = re.compile(
        r"\b(?:"
        + "|".join(re.escape(key) for key in sorted(mapping, key=len, reverse=True))
        + r")\b"
    )
    # pattern.sub recorre cada match. El lambda recibe ese match y
    # devuelve mapping[texto_encontrado], que es lo que se escribe.
    return pattern.sub(lambda match: mapping[match.group(0)], text)

def _clean_spaces(text: str) -> str:
    text = re.sub(r"\.{2,}", ".", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_shipment_fields(data: dict[str, Any]) -> dict[str, Any]:
    """Normaliza una copia con campos limpios. No valida ni llama API."""
    normalized = {
        "name_receiver": str(data.get("name_receiver") or "").strip().upper(),
        "street": str(data.get("street") or "").strip().upper(),
        "num_street": str(data.get("num_street") or "").strip().upper(),
        "phone": str(data.get("phone") or "").strip().upper(),
        "address_reference": str(data.get("address_reference") or "").strip().upper(),
    }

    for key, value in replacements_vocales.items():
        for field in normalized:
            normalized[field] = normalized[field].replace(key, value)

    normalized["name_receiver"] = normalize_name_receiver(normalized["name_receiver"])
    normalized["street"] = normalize_street(normalized["street"])
    normalized["num_street"] = normalize_num_street(normalized["num_street"])
    normalized["phone"] = normalize_phone(normalized["phone"])
    normalized["address_reference"] = normalize_address_reference(
        normalized["address_reference"]
    )
    return normalized


def quitar_puntos_entre_letras(text: str) -> str:
    # Letra . Letra
    text = re.sub(r"(?<=[A-Za-zÁÉÍÓÚÜÑáéíóúüñ])\.(?=[A-Za-zÁÉÍÓÚÜÑáéíóúüñ])", "", text)
    # Letra . Espacio
    text = re.sub(r"(?<=[A-Za-zÁÉÍÓÚÜÑáéíóúüñ])\.(?=\s)", "", text)
    # Espacio . Letra
    text = re.sub(r"(?<=\s)\.(?=[A-Za-zÁÉÍÓÚÜÑáéíóúüñ])", "", text)
    return text


def replace_special_characters(
    text: str,
    conservar_parentesis: bool = False,
    conservar_diagonal: bool = False,
) -> str:
    if not text:
        return text
    if not conservar_parentesis:
        text = text.replace("(", "").replace(")", "")
    if not conservar_diagonal:
        text = text.replace("/", "")

    for key, value in replacements_especiales.items():
        text = text.replace(key, value)
    return _clean_spaces(text)


def normalize_name_receiver(name: str) -> str:
    name_normalized = _replace_whole_words(name, replacements_frases_largas)
    name_normalized = _replace_whole_words(name_normalized, replacements_cargos)
    return replace_special_characters(name_normalized, conservar_diagonal=True)


def normalize_street(street: str) -> str:
    street_normalized = _replace_whole_words(street, replacements_direcciones)
    return replace_special_characters(street_normalized)


def normalize_num_street(num_street: str) -> str:
    if not num_street:
        return ""
    # Conserva únicamente puntos entre números.
    num_street_normalized = quitar_puntos_entre_letras(num_street)
    num_street_normalized = replace_special_characters(num_street_normalized)
    num_street_normalized = _replace_whole_words(
        num_street_normalized,
        {word: "" for word in ("NUMERO", "NUM", "NOM", "NO", "TEL", "TELEFONO")},
    )
    return _clean_spaces(num_street_normalized)


def normalize_phone(phone: str) -> str:
    if not phone:
        return ""
    phone_normalized = phone.replace(".", "")
    phone_normalized = replace_special_characters(phone_normalized)
    phone_normalized = _replace_whole_words(
        phone_normalized,
        {word: "" for word in ("TELEFONO", "TEL")},
    )
    return _clean_spaces(phone_normalized)


def normalize_address_reference(address_reference: str) -> str:
    if not address_reference:
        return ""
    address_reference_normalized = _replace_whole_words(
        address_reference, replacements_direcciones
    )
    return replace_special_characters(address_reference_normalized)

