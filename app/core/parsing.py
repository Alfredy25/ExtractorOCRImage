"""Parsing y normalización del JSON de la IA."""
import json
import re

from app.core.models import CamposDestinatario, ExtraccionDestinatario


def _normalize(s: str | None) -> str:
    """Normalización mínima: strip y colapsar espacios dobles."""
    if s is None:
        return ""
    s = str(s).strip()
    return re.sub(r"\s+", " ", s)


def parse_extraccion(raw: str) -> ExtraccionDestinatario:
    """Parsea el JSON de la IA y devuelve ExtraccionDestinatario validado."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Intenta limpiar marcadores de código
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.IGNORECASE | re.MULTILINE)
        cleaned = cleaned.strip()
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            return _fallback_extraccion()

    try:
        campos = data.get("campos") or {}
        return ExtraccionDestinatario(
            destinatario_raw=_normalize(data.get("destinatario_raw", "")) or "",
            campos=CamposDestinatario(
                nombre_o_titulo=_normalize(campos.get("nombre_o_titulo", "")),
                cargo_dependencia=_normalize(campos.get("cargo_dependencia", "")),
                direccion=_normalize(campos.get("direccion", "")),
                colonia=_normalize(campos.get("colonia", "")),
                municipio_o_alcaldia=_normalize(campos.get("municipio_o_alcaldia", "")),
                estado=_normalize(campos.get("estado", "")),
                codigo_postal=_normalize(campos.get("codigo_postal", "")),
                extras=_normalize(campos.get("extras", "")),
                contacto=_normalize(campos.get("contacto", "")),
                indicaciones=_normalize(campos.get("indicaciones", "")),
            ),
            observaciones_ia=_normalize(data.get("observaciones_ia", "")),
        )
    except Exception:
        return _fallback_extraccion()


def _fallback_extraccion() -> ExtraccionDestinatario:
    """Fallback cuando la IA no devuelve JSON válido."""
    return ExtraccionDestinatario(
        destinatario_raw="",
        campos=CamposDestinatario(
            nombre_o_titulo="",
            cargo_dependencia="",
            direccion="",
            colonia="",
            municipio_o_alcaldia="",
            estado="",
            codigo_postal="",
            extras="",
            contacto="",
            indicaciones="",
        ),
        observaciones_ia="No se obtuvo JSON válido del modelo.",
    )
