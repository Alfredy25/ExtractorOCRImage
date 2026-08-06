"""Transporte HTTP para consultar coberturas Paquetexpress."""

from __future__ import annotations

from typing import Any

import httpx

from app.config import API_TIMEOUT_SECONDS, COVERTURAS_ENDPOINT, api_abs_url


class CoveragesApiError(Exception):
    """Fallo HTTP al consultar cobertura."""


class CoveragesSessionExpiredError(CoveragesApiError):
    """El backend rechazó el JWT con estado 401."""


class CoverageNotFoundError(CoveragesApiError):
    """No existe cobertura para el código postal consultado."""


def get_coverages(postal_code: str, token: str) -> list[dict[str, Any]]:
    """Consulta coberturas por código postal."""
    cp = str(postal_code or "").strip()
    if not cp:
        raise CoveragesApiError("El código postal es obligatorio para consultar cobertura.")

    endpoint = f"{COVERTURAS_ENDPOINT.rstrip('/')}/"
    url = api_abs_url(endpoint)
    headers = {"Authorization": f"Bearer {token}"}
    params = {"cp": cp}
    try:
        with httpx.Client(timeout=API_TIMEOUT_SECONDS) as client:
            response = client.get(url, headers=headers, params=params)
    except httpx.TimeoutException as exc:
        raise CoveragesApiError("Tiempo de espera al consultar cobertura.") from exc
    except httpx.RequestError as exc:
        raise CoveragesApiError(f"No se pudo conectar con el servidor: {exc}") from exc

    if response.status_code == 401:
        raise CoveragesSessionExpiredError(
            "Sesión caducada o no autorizado. Vuelva a iniciar sesión."
        )
    if response.status_code == 404:
        raise CoverageNotFoundError(_http_error_detail(response))
    if response.status_code >= 400:
        raise CoveragesApiError(
            f"No se pudo consultar cobertura (código {response.status_code}): "
            f"{_http_error_detail(response)}"
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise CoveragesApiError("La respuesta del servidor no es JSON válido.") from exc

    if not isinstance(payload, list):
        raise CoveragesApiError(
            "La respuesta del servidor no es una lista de coberturas reconocible."
        )
    return [item for item in payload if isinstance(item, dict)]


def _http_error_detail(response: httpx.Response) -> str:
    try:
        data = response.json()
        if isinstance(data, dict):
            detail = data.get("detail")
            if isinstance(detail, str):
                return detail
            if isinstance(detail, list):
                return "; ".join(
                    str(item.get("msg", item)) if isinstance(item, dict) else str(item)
                    for item in detail
                )
    except ValueError:
        pass
    text = (response.text or "").strip()
    return text[:500] if text else "(sin detalle)"
