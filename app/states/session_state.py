"""Estado de autenticación en memoria para el proceso actual."""

from __future__ import annotations

_access_token: str | None = None


def get_access_token() -> str | None:
    """Devuelve el JWT actual o ``None`` si no hay sesión."""
    return _access_token


def set_access_token(token: str) -> None:
    """Guarda el JWT de la sesión autenticada."""
    global _access_token
    _access_token = token


def clear_access_token() -> None:
    """Elimina el JWT de la sesión actual."""
    global _access_token
    _access_token = None
