"""Caso de uso de autenticación y gestión de sesión."""

from app.api.auth_api import AuthClientError, AuthError, authenticate
from app.states.session_state import (clear_access_token, get_access_token, 
                                        set_access_token)
def login(email: str, password: str) -> None:
    """Autentica al usuario y conserva el JWT solo en memoria."""
    token = authenticate(email, password)
    set_access_token(token)


__all__ = ["AuthClientError", "AuthError", "clear_access_token", 
            "get_access_token", "login"]
