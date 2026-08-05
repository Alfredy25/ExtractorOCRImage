"""Cliente HTTP de autenticación contra el backend FastAPI."""

from __future__ import annotations

import logging
from typing import Optional

import httpx
from pydantic import ValidationError

from app.config import API_TIMEOUT_SECONDS, LOGIN_ENDPOINT, api_abs_url
from app.models.auth import LoginRequest

logger = logging.getLogger(__name__)


class AuthError(Exception):
    """Credenciales rechazadas (401/403). Mensaje apto para mostrar al usuario."""


class AuthClientError(Exception):
    """Red, timeout, 5xx o cuerpo de respuesta inutilizable."""


def authenticate(email: str, password: str) -> str:
    """
    POST LOGIN_ENDPOINT y devuelve el JWT validado.

    Cuerpo JSON: ``{"email": "...", "password": "..."}`` (p. ej. Postman raw JSON).

    Raises:
        AuthError: correo/contraseña incorrectos.
        AuthClientError: conexión, timeout o respuesta inválida.
    """
    credentials = _validate_credentials(email, password)

    url = api_abs_url(LOGIN_ENDPOINT)
    # JSON crudo (p. ej. Postman Body raw), alineado con el contrato del backend FastAPI.

    try:
        with httpx.Client(timeout=API_TIMEOUT_SECONDS) as client:
            response = client.post(
                url,
                json=credentials.model_dump(mode="json"),
            )
    except httpx.TimeoutException as e:
        logger.warning("login timeout: %s", e)
        raise AuthClientError("Tiempo de espera agotado al contactar el servidor.") from e
    except httpx.RequestError as e:
        logger.warning("login request error: %s", e)
        raise AuthClientError(f"No se pudo conectar con el servidor: {e}") from e

    if response.status_code in (401, 403):
        raise AuthError("Correo electrónico o contraseña incorrectos.")

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

    return token


def _validate_credentials(email: str, password: str) -> LoginRequest:
    """Construye credenciales validadas y traduce errores para la interfaz."""
    try:
        return LoginRequest(email=(email or "").strip(), password=password)
    except ValidationError as exc:
        invalid_fields = {error["loc"][0] for error in exc.errors()}
        if "email" in invalid_fields:
            raise AuthError("Indique un correo electrónico válido.") from exc
        if "password" in invalid_fields:
            raise AuthError("La contraseña debe tener al menos 6 caracteres.") from exc
        raise AuthError("Las credenciales proporcionadas no son válidas.") from exc


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
