"""Modelos Pydantic para el esquema JSON de extracción."""
from pydantic import BaseModel, Field


class CamposDestinatario(BaseModel):
    """Campos estructurados del destinatario."""

    nombre_o_titulo: str = ""
    cargo_dependencia: str = ""
    direccion: str = ""
    colonia: str = ""
    municipio_o_alcaldia: str = ""
    estado: str = ""
    codigo_postal: str = ""
    extras: str = ""
    contacto: str = ""
    indicaciones: str = ""


class ExtraccionDestinatario(BaseModel):
    """Esquema JSON esperado de la IA."""

    destinatario_raw: str = ""
    campos: CamposDestinatario = Field(default_factory=CamposDestinatario)
    observaciones_ia: str = ""
