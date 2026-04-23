# [NUEVO] Cliente HTTP de autenticación hacia FastAPI. La UI no importa este módulo para
# hacer requests: solo orquesta; el token se lee vía get_access_token() desde core
# (p. ej. repository) tras un login exitoso gestionado también desde core/main.

"""Autenticación contra el backend FastAPI: login y JWT solo en memoria (por proceso)."""

from __future__ import annotations

import logging
from typing import Optional

import httpx

from app.config import API_TIMEOUT_SECONDS, LOGIN_ENDPOINT, api_abs_url

logger = logging.getLogger(__name__)

# JWT en memoria: un proceso / un usuario a la vez; al cerrar la app se pierde.
_access_token: Optional[str] = None


class AuthError(Exception):
    """Credenciales rechazadas (401/403). Mensaje apto para mostrar al usuario."""


class AuthClientError(Exception):
    """Red, timeout, 5xx o cuerpo de respuesta inutilizable."""


def get_access_token() -> Optional[str]:
    """Devuelve el JWT actual o None si no hay sesión iniciada."""
    return _access_token


def clear_access_token() -> None:
    """Olvida el token (p. ej. al cerrar sesión o antes de un nuevo login)."""
    global _access_token
    _access_token = None


def login(usuario: str, password: str) -> None:
    """
    POST LOGIN_ENDPOINT: autentica y guarda el JWT en memoria.

    Cuerpo JSON: ``{"username": "...", "password": "..."}`` (p. ej. Postman raw JSON).

    Raises:
        AuthError: usuario/contraseña incorrectos.
        AuthClientError: conexión, timeout o respuesta inválida.
    """
    global _access_token

    u = (usuario or "").strip()
    if not u:
        raise AuthError("Indique un usuario.")
    if not password:
        raise AuthError("Indique una contraseña.")

    url = api_abs_url(LOGIN_ENDPOINT)
    # JSON crudo (p. ej. Postman Body raw), alineado con el contrato del backend FastAPI.

    try:
        with httpx.Client(timeout=API_TIMEOUT_SECONDS) as client:
            response = client.post(
                url,
                json={"username": u, "password": password},
            )
    except httpx.TimeoutException as e:
        logger.warning("login timeout: %s", e)
        raise AuthClientError("Tiempo de espera agotado al contactar el servidor.") from e
    except httpx.RequestError as e:
        logger.warning("login request error: %s", e)
        raise AuthClientError(f"No se pudo conectar con el servidor: {e}") from e

    if response.status_code in (401, 403):
        raise AuthError("Usuario o contraseña incorrectos.")

    if response.status_code >= 400:
        detail = _extract_error_detail(response)
        raise AuthClientError(
            f"Error del servidor (código {response.status_code}): {detail}"
        )

    try:
        body = response.json()
    except ValueError as e:
        raise AuthClientError("La respuesta del servidor no es JSON válido.") from e

    token = _parse_token_from_body(body)
    if not token:
        raise AuthClientError(
            "La respuesta no contiene un token de acceso reconocido (access_token)."
        )

    _access_token = token


def _parse_token_from_body(body: object) -> Optional[str]:
    """Acepta {"access_token": "..."} o {"token": "..."} como dict raíz."""
    if not isinstance(body, dict):
        return None
    t = body.get("access_token") or body.get("token")
    if isinstance(t, str) and t.strip():
        return t.strip()
    return None


def _extract_error_detail(response: httpx.Response) -> str:
    try:
        data = response.json()
        if isinstance(data, dict):
            d = data.get("detail")
            if isinstance(d, str):
                return d
            if isinstance(d, list):
                parts = []
                for item in d:
                    if isinstance(item, dict) and "msg" in item:
                        parts.append(str(item.get("msg")))
                    else:
                        parts.append(str(item))
                return "; ".join(parts) if parts else str(d)
        return str(data)[:500]
    except ValueError:
        pass
    text = (response.text or "").strip()
    return text[:500] if text else "(sin detalle)"
