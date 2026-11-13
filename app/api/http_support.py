"""Utilidades compartidas por los clientes HTTP nuevos.

Cada módulo de ``app/api`` sigue siendo el dueño de sus excepciones. Aquí solo
vive el transporte (timeout, conexión, 401) y la lectura de errores JSON.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.config import API_TIMEOUT_SECONDS


class TransportError(Exception):
    """Timeout o fallo de red antes de recibir un status HTTP."""


class SessionExpiredError(Exception):
    """El backend rechazó el JWT con estado 401."""


def bearer_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def request(
    method: str,
    url: str,
    token: str,
    *,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
) -> httpx.Response:
    """Ejecuta una llamada autenticada y deja los 4xx (salvo 401) al caller."""
    try:
        with httpx.Client(timeout=API_TIMEOUT_SECONDS) as client:
            response = client.request(
                method,
                url,
                headers=bearer_headers(token),
                params=params,
                json=json_body,
            )
    except httpx.TimeoutException as exc:
        raise TransportError("Tiempo de espera agotado.") from exc
    except httpx.RequestError as exc:
        raise TransportError(f"No se pudo conectar con el servidor: {exc}") from exc

    if response.status_code == 401:
        raise SessionExpiredError(
            "Sesión caducada o no autorizado. Vuelva a iniciar sesión."
        )
    return response


def error_detail(response: httpx.Response) -> str:
    try:
        data = response.json()
    except ValueError:
        data = None
    if isinstance(data, dict):
        detail = data.get("detail")
        if isinstance(detail, str) and detail.strip():
            return detail
        if isinstance(detail, dict):
            message = detail.get("msg") or detail.get("message")
            if isinstance(message, str) and message.strip():
                return message
        if isinstance(detail, list):
            parts: list[str] = []
            for item in detail:
                if isinstance(item, dict):
                    parts.append(str(item.get("msg") or item.get("message") or item))
                else:
                    parts.append(str(item))
            if parts:
                return "; ".join(parts)
    text = (response.text or "").strip()
    return text[:500] if text else "(sin detalle)"


def validation_errors(response: httpx.Response) -> list[dict[str, str]]:
    """Normaliza un 422 a ``[{"field", "message"}]``."""
    try:
        data = response.json()
    except ValueError:
        return [{"field": "body", "message": error_detail(response)}]
    if isinstance(data, dict) and isinstance(data.get("errors"), list):
        parsed: list[dict[str, str]] = []
        for item in data["errors"]:
            if not isinstance(item, dict):
                parsed.append({"field": "body", "message": str(item)})
                continue
            parsed.append(
                {
                    "field": str(item.get("field") or "body"),
                    "message": str(item.get("message") or item.get("msg") or "Valor inválido"),
                }
            )
        if parsed:
            return parsed
    return [{"field": "body", "message": error_detail(response)}]


def json_body(response: httpx.Response) -> Any:
    try:
        if not response.content:
            return {}
        return response.json()
    except ValueError as exc:
        raise TransportError("La respuesta del servidor no es JSON válido.") from exc


def duplicate_id(response: httpx.Response, key: str) -> int | None:
    """Lee ``detail.{key}`` de un 409 con cuerpo objeto."""
    try:
        data = response.json()
    except ValueError:
        return None
    detail = data.get("detail") if isinstance(data, dict) else None
    if not isinstance(detail, dict) or detail.get(key) is None:
        return None
    try:
        return int(detail[key])
    except (TypeError, ValueError):
        return None


def query_params(**values: Any) -> dict[str, Any]:
    """Quita parámetros vacíos para no enviar ``null`` en la query."""
    params: dict[str, Any] = {}
    for key, value in values.items():
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        params[key] = value
    return params
