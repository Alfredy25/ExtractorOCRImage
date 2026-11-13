"""Normalización de texto para catálogos, destinatario y edición de envío."""

from __future__ import annotations

import re
from typing import Any

_ACCENTS = str.maketrans({
    "Á": "A",
    "É": "E",
    "Í": "I",
    "Ó": "O",
    "Ú": "U",
    "Ü": "U",
})

_SPECIAL_CHARS = {
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

ORG_ABBREVIATIONS = {
    "SERVICIO DE ADMINISTRACION TRIBUTARIA": "S.A.T.",
    "SECRETARIA DE ADMINISTRACION TRIBUTARIA": "S.A.T.",
    "SECRETARIA DE CONTRALORIA GENERAL": "S.C.E.",
    "CONTRALORIA GENERAL DEL ESTADO": "C.G.E.",
    "ORGANO INTERNO DE CONTROL": "O.I.C.",
    "ORGANO DE CONTROL INTERNO": "O.I.C.",
    "BAJA CALIFORNIA SUR": "B.C.S.",
    "SAN LUIS POTOSI": "S.L.P.",
    "UNIVERSIDAD": "UNI.",
    "AUTONOMA": "AUT.",
    "ADMINISTRACION": "ADMON.",
    "SECRETARIA": "SECRET.A",
    "ESTADO": "EDO",
}

ROLE_ABBREVIATIONS = {
    "ADMINISTRADORA DESCONCENTRADA DE RECAUDACION": "ADM. DESC. DE REC.",
    "ADMINISTRADOR DESCONCENTRADA DE RECAUDACION": "ADM. DESC. DE REC.",
    "BAJA CALIFORNIA SUR": "B.C.S.",
    "SAN LUIS POTOSI": "S.L.P.",
    "ADMINISTRADORA": "ADMIN.",
    "ADMINISTRADOR": "ADMIN.",
    "ADMINISTRACION": "ADMON.",
    "SECRETARIA": "SECRET.A",
    "SECRETARIO": "SEC.",
    "PRESIDENTA": "PDTA.",
    "PRESIDENTE": "PDTE.",
    "DIRECTORA": "DIR.A",
    "DIRECTOR": "DIR.",
    "GOBERNADOR": "GOB.",
    "UNIVERSIDAD": "UNI",
    "AUTONOMA": "AUT.",
    "PROFESORA": "PROFA.",
    "PROFESOR": "PROF.",
    "DIPUTADA": "DIP.",
    "DIPUTADO": "DIP.",
    "SENADORA": "SEN.",
    "SENADOR": "SEN.",
    "DOCTORA": "DRA.",
    "DOCTOR": "DR.",
    "MAESTRA": "MTRA.",
    "MAESTRO": "MTRO.",
    "TITULAR": "TIT.",
    "GENERAL": "GRAL.",
    "ESTADO": "EDO",
}

TITLE_ABBREVIATIONS = {
    "CONTADOR PUBLICO": "C.P.",
    "CIUDADANO": "C.",
    "CIUDADANA": "C.",
    "ABOGADO": "ABG.",
    "ABOGADA": "ABG.",
    "ACTUARIO": "ACT.",
    "ACTUARIA": "ACT.",
    "DOCTORA": "DRA.",
    "DOCTOR": "DR.",
    "GOBERNADORA": "GOB.",
    "GOBERNADOR": "GOB.",
    "INGENIERA": "ING.",
    "INGENIERO": "ING.",
    "LICENCIADA": "LIC.",
    "LICENCIADO": "LIC.",
    "MAESTRA": "MTRA.",
    "MAESTRO": "MTRO.",
    "PROFESORA": "PROFA.",
    "PROFESOR": "PROF.",
    "SENORA": "SRA.",
    "SENOR": "SR.",
}

STREET_ABBREVIATIONS = {
    "SIN NUMERO": "SN.",
    "S/N": "SN",
    "BOULEVARD": "BLVD.",
    "CARRETERA": "CARR.",
    "KILOMETRO": "KM.",
    "EDIFICIO": "EDIF.",
    "AVENIDA": "AV.",
    "NUMERO": "NUM.",
    "CALLE": "C.",
}

_PHONE_JUNK = ("TELEFONO", "NUMERO", "NUM", "NOM", "TEL", "NO")

# El nombre del envío junta título, cargo y organización en un solo campo.
# UNIVERSIDAD queda UNI (sin punto), como ya se abreviaba ahí.
_SHIPMENT_NAME_ABBREVIATIONS = {
    **ROLE_ABBREVIATIONS,
    **TITLE_ABBREVIATIONS,
    "SECRETARIA DE ADMINISTRACION TRIBUTARIA": "S.A.T.",
    "SECRETARIA DE CONTRALORIA GENERAL": "S.C.E.",
    "CONTRALORIA GENERAL DEL ESTADO": "C.G.E.",
    "ORGANO INTERNO DE CONTROL": "O.I.C.",
    "ORGANO DE CONTROL INTERNO": "O.I.C.",
    "SERVICIO DE ADMINISTRACION TRIBUTARIA": "S.A.T.",
    "UNIVERSIDAD": "UNI",
    "CIUDAD": "C.D.",
}

_NUM_STREET_TERMS = {
    **STREET_ABBREVIATIONS,
    **{word: "" for word in _PHONE_JUNK},
}

_JUNK_PATTERN = re.compile(
    r"(?<!\w)(?:"
    + "|".join(re.escape(word) for word in sorted(_PHONE_JUNK, key=len, reverse=True))
    + r")\.?(?!\w)"
)


def clean_base_text(
    text: str,
    *,
    drop_slash: bool = False,
    drop_parens: bool = False,
) -> str:
    """Mayúsculas, vocales sin acento, signos y espacios. Conserva el punto."""
    value = str(text or "").upper().translate(_ACCENTS).replace("?", "Ñ")
    if drop_parens:
        value = value.replace("(", "").replace(")", "")
    if drop_slash:
        value = value.replace("/", "")
    for char, replacement in _SPECIAL_CHARS.items():
        value = value.replace(char, replacement)
    return _collapse(value)


def normalize_full_name(text: str) -> str:
    """Nombre del destinatario: solo la regla base."""
    return clean_base_text(text)


def normalize_organization(text: str) -> str:
    """Organización: regla base y abreviaturas de institución."""
    return _apply_terms(clean_base_text(text), ORG_ABBREVIATIONS)


def normalize_job_role(text: str) -> str:
    """Cargo: regla base y abreviaturas de puesto."""
    return _apply_terms(clean_base_text(text), ROLE_ABBREVIATIONS)


def normalize_title(text: str) -> str:
    """Título: regla base y abreviaturas de tratamiento."""
    return _apply_terms(clean_base_text(text), TITLE_ABBREVIATIONS)


def normalize_phone(text: str) -> str:
    """Teléfono o extensión: regla base y palabras que no son el número."""
    return _collapse(_JUNK_PATTERN.sub("", clean_base_text(text)))


def normalize_street(text: str) -> str:
    """Calle o número del formulario: regla base y abreviaturas de vía."""
    return _apply_terms(clean_base_text(text), STREET_ABBREVIATIONS)


def normalize_email(text: str) -> str:
    """Correo en minúsculas, sin la regla base."""
    return str(text or "").strip().lower()


def normalize_name_receiver(name: str) -> str:
    """Nombre compuesto del envío. Conserva la diagonal y quita paréntesis."""
    cleaned = clean_base_text(name, drop_parens=True)
    return _apply_terms(cleaned, _SHIPMENT_NAME_ABBREVIATIONS)


def normalize_num_street(num_street: str) -> str:
    """Número del envío: quita puntos entre letras y palabras que no son el número."""
    if not str(num_street or "").strip():
        return ""
    cleaned = clean_base_text(num_street, drop_slash=True, drop_parens=True)
    cleaned = _strip_letter_periods(cleaned)
    return _apply_terms(cleaned, _NUM_STREET_TERMS)


def normalize_address_reference(address_reference: str) -> str:
    """Referencia del envío, con las abreviaturas de la calle."""
    cleaned = clean_base_text(address_reference, drop_slash=True, drop_parens=True)
    return _apply_terms(cleaned, STREET_ABBREVIATIONS)


def normalize_shipment_fields(data: dict[str, Any]) -> dict[str, Any]:
    """Copia normalizada de los campos sueltos de la edición de envío."""

    def _text(key: str) -> str:
        return str(data.get(key) or "")

    return {
        "name_receiver": normalize_name_receiver(_text("name_receiver")),
        "street": _apply_terms(
            clean_base_text(_text("street"), drop_slash=True, drop_parens=True),
            STREET_ABBREVIATIONS,
        ),
        "num_street": normalize_num_street(_text("num_street")),
        "phone": _collapse(
            _JUNK_PATTERN.sub(
                "",
                clean_base_text(_text("phone"), drop_slash=True, drop_parens=True),
            )
        ),
        "address_reference": normalize_address_reference(_text("address_reference")),
    }


def _apply_terms(text: str, mapping: dict[str, str]) -> str:
    if not text or not mapping:
        return text
    pattern = re.compile(
        r"(?<!\w)(?:"
        + "|".join(re.escape(key) for key in sorted(mapping, key=len, reverse=True))
        + r")(?!\w)"
    )
    return _collapse(pattern.sub(lambda match: mapping[match.group(0)], text))


def _strip_letter_periods(text: str) -> str:
    """Quita el punto entre letras. Conserva el punto entre números."""
    letters = r"A-Za-zÁÉÍÓÚÜÑáéíóúüñ"
    text = re.sub(rf"(?<=[{letters}])\.(?=[{letters}])", "", text)
    text = re.sub(rf"(?<=[{letters}])\.(?=\s)", "", text)
    text = re.sub(rf"(?<=\s)\.(?=[{letters}])", "", text)
    return text


def _collapse(text: str) -> str:
    text = re.sub(r"\.{2,}", ".", text)
    return re.sub(r"\s+", " ", text).strip()
