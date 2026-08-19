"""Transporte HTTP para crear, consultar y actualizar envíos Paquetexpress."""

from __future__ import annotations

from typing import Any
from app.models.shipping import ShippingDto
import httpx
from datetime import datetime
from pydantic import ValidationError

from app.config import API_TIMEOUT_SECONDS, ENVIOS_PX_ENDPOINT, api_abs_url


class ShipmentsApiError(Exception):
    """Fallo HTTP al crear envíos Paquetexpress."""


class ShipmentsSessionExpiredError(ShipmentsApiError):
    """El backend rechazó el JWT con estado 401."""


def create_shipment(payload: dict[str, Any], token: str) -> dict[str, Any]:
    """Crea un envío Paquetexpress y devuelve el cuerpo de respuesta."""
    url = api_abs_url(ENVIOS_PX_ENDPOINT)
    headers = {"Authorization": f"Bearer {token}"}
    try:
        with httpx.Client(timeout=API_TIMEOUT_SECONDS) as client:
            response = client.post(url, headers=headers, json=payload)
    except httpx.TimeoutException as exc:
        raise ShipmentsApiError("Tiempo de espera al crear el envío.") from exc
    except httpx.RequestError as exc:
        raise ShipmentsApiError(f"No se pudo conectar con el servidor: {exc}") from exc

    if response.status_code == 401:
        raise ShipmentsSessionExpiredError(
            "Sesión caducada o no autorizado. Vuelva a iniciar sesión."
        )
    if response.status_code >= 400:
        raise ShipmentsApiError(
            f"No se pudo crear el envío (código {response.status_code}): "
            f"{_http_error_detail(response)}"
        )

    try:
        body = response.json() if response.content else {}
    except ValueError as exc:
        raise ShipmentsApiError("La respuesta del servidor no es JSON válido.") from exc
    return body if isinstance(body, dict) else {"data": body}


def update_shipment(id_shipping: int, payload: dict[str, Any], token: str) -> ShippingDto:
    """Actualiza un envío Paquetexpress y devuelve el ``ShippingDto`` resultante."""
    url = api_abs_url(f"{ENVIOS_PX_ENDPOINT}{id_shipping}")
    headers = {"Authorization": f"Bearer {token}"}
    try:
        with httpx.Client(timeout=API_TIMEOUT_SECONDS) as client:
            response = client.put(url, headers=headers, json=payload)
    except httpx.TimeoutException as exc:
        raise ShipmentsApiError("Tiempo de espera al actualizar el envío.") from exc
    except httpx.RequestError as exc:
        raise ShipmentsApiError(f"No se pudo conectar con el servidor: {exc}") from exc

    if response.status_code == 401:
        raise ShipmentsSessionExpiredError(
            "Sesión caducada o no autorizado. Vuelva a iniciar sesión."
        )
    if response.status_code >= 400:
        raise ShipmentsApiError(
            f"No se pudo actualizar el envío (código {response.status_code}): "
            f"{_http_error_detail(response)}"
        )

    try:
        body = response.json() if response.content else {}
    except ValueError as exc:
        raise ShipmentsApiError("La respuesta del servidor no es JSON válido.") from exc
    if not isinstance(body, dict):
        raise ShipmentsApiError(
            "La API devolvió un formato inesperado: se esperaba un objeto."
        )
    try:
        return ShippingDto.model_validate(body)
    except ValidationError as exc:
        raise ShipmentsApiError(
            f"El envío actualizado tiene formato inválido. {exc}"
        ) from exc


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


def list_by_date_range(desde: datetime, hasta: datetime, token: str) -> list[ShippingDto]:
    """Lista los envios de fechas entre desde y hasta."""
    url = api_abs_url(ENVIOS_PX_ENDPOINT)
    headers = {"Authorization": f"Bearer {token}"}
    params: dict[str, Any] = {
        "fecha_inicio": desde, # isoformat()
        "fecha_fin": hasta,  # .isoformat()
    }
    print("fecha_inicio: ", params["fecha_inicio"])
    print("fecha_fin: ", params["fecha_fin"])
    try:
        with httpx.Client(timeout=API_TIMEOUT_SECONDS) as client:
            response = client.get(url, headers=headers, params=params)
    except httpx.TimeoutException as exc:
        raise ShipmentsApiError("Tiempo de espera al obtener los envíos.") from exc
    except httpx.RequestError as exc:
        raise ShipmentsApiError(f"No se pudo conectar con el servidor: {exc}") from exc

    if response.status_code == 401:
        raise ShipmentsSessionExpiredError(
            "Sesión caducada o no autorizado. Vuelva a iniciar sesión."
        )
    if response.status_code >= 400:
         raise ShipmentsApiError(
            f"No se pudo obtener los envíos (código {response.status_code}): "
            f"{_http_error_detail(response)}"
        )
    try:
        body = response.json() if response.content else {}
    except ValueError as exc:
        raise ShipmentsApiError("La respuesta del servidor no es JSON válido.") from exc
    if not isinstance(body, list):
        raise ShipmentsApiError(
            "La API devolvió un formato inesperado: se esperaba una lista."
        )
    
    try:
        return [ShippingDto.model_validate(obj) for obj in body]
    except ValidationError as exc:
        raise ShipmentsApiError(f"Uno o más envíos devueltos por la API tienen formato inválido. {exc}") from exc



