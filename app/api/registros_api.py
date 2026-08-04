"""Transporte HTTP para crear y consultar registros OCR."""

from __future__ import annotations

from typing import Any

import httpx

from app.config import API_TIMEOUT_SECONDS, REGISTROS_ENDPOINT, api_abs_url


class RegistrosApiError(Exception):
    """Fallo HTTP con mensaje apto para la interfaz."""


class RegistrosSessionExpiredError(RegistrosApiError):
    """El backend rechazó el JWT con estado 401."""


def create_registro(payload: dict[str, Any], token: str) -> int:
    """Crea un registro y devuelve el identificador asignado."""
    response = _request("POST", token, json=payload, 
    timeout_message="Tiempo de espera al guardar el registro.")
    try:
        body = response.json() if response.content else {}
    except ValueError as exc:
        raise RegistrosApiError("La respuesta del servidor no es JSON válido.") from exc

    registro_id = _parse_new_id(body)
    if registro_id is None:
        raise RegistrosApiError(
            "El servidor no devolvió el identificador del registro (campo id)."
        )
    return registro_id


def list_registros(params: dict[str, Any], token: str) -> list[dict]:
    """Consulta registros y normaliza las variantes de lista del backend."""
    response = _request("GET", token, params=params, 
    timeout_message="Tiempo de espera al consultar registros.")
    try:
        payload = response.json()
    except ValueError as exc:
        raise RegistrosApiError("La respuesta del servidor no es JSON válido.") from exc
    return _parse_registros_list_json(payload)


def _request(method: str, token: str, *, timeout_message: str, **kwargs) -> httpx.Response:
    url = api_abs_url(REGISTROS_ENDPOINT)
    headers = {"Authorization": f"Bearer {token}"}
    try:
        with httpx.Client(timeout=API_TIMEOUT_SECONDS) as client:
            response = client.request(method, url, headers=headers, **kwargs)
    except httpx.TimeoutException as exc:
        raise RegistrosApiError(timeout_message) from exc
    except httpx.RequestError as exc:
        raise RegistrosApiError(f"No se pudo conectar con el servidor: {exc}") from exc

    if response.status_code == 401:
        raise RegistrosSessionExpiredError(
            "Sesión caducada o no autorizado. Vuelva a iniciar sesión."
        )
    if response.status_code >= 400:
        message = (
            "No se pudo guardar"
            if method == "POST"
            else "No se pudieron obtener registros"
        )
        raise RegistrosApiError(
            f"{message} (código {response.status_code}): "
            f"{_http_error_detail(response)}"
        )
    return response


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


def _coerce_positive_id(value: Any) -> int | None:
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, str) and value.isdigit():
        integer = int(value)
        return integer if integer > 0 else None
    return None


def _parse_new_id(body: object) -> int | None:
    if not isinstance(body, dict):
        return None
    for key in ("id", "registro_id"):
        registro_id = _coerce_positive_id(body.get(key))
        if registro_id is not None:
            return registro_id
    nested = body.get("registro")
    if not isinstance(nested, dict):
        nested = body.get("data")
    if isinstance(nested, dict):
        for key in ("id", "registro_id"):
            registro_id = _coerce_positive_id(nested.get(key))
            if registro_id is not None:
                return registro_id
    return None


def _parse_registros_list_json(data: Any) -> list[dict]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ("items", "registros", "data", "results"):
            inner = data.get(key)
            if isinstance(inner, list):
                return [item for item in inner if isinstance(item, dict)]
    raise RegistrosApiError(
        "La respuesta del servidor no es una lista de registros reconocible."
    )
