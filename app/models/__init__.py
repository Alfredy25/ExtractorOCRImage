"""Modelos de dominio y DTOs."""

from app.models.extraction import CamposDestinatario, ExtraccionDestinatario
from app.models.registro import RegistroFieldError, RegistroRequest, validate_registro

__all__ = [
    "CamposDestinatario",
    "ExtraccionDestinatario",
    "RegistroFieldError",
    "RegistroRequest",
    "validate_registro",
]
