"""Fachada de persistencia de registros vía API REST (sin almacenamiento local)."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from app.api.registros_api import (
    RegistrosApiError as RepositoryApiError,
    RegistrosSessionExpiredError as RepositorySessionExpiredError,
    create_registro,
    list_registros,
)
from app.services.auth_service import get_access_token


def _field_to_db(value: str | None, is_destinatario_raw: bool = False) -> str | None:
    """
    Mapeo UI -> BD:
    - Vacío -> NULL (excepto destinatario_raw que puede ser "")
    - "ILEGIBLE" (case-insensitive) -> "ILEGIBLE"
    - Otro texto -> MAYÚSCULAS
    """
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None if not is_destinatario_raw else ""
    if "ilegible" in s.lower():
        return "ILEGIBLE"
    return s.upper()


def _sede_for_api(record: dict) -> str:
    """
    ``RegistroBase.sede`` en FastAPI: ``Literal['AJUSCO', 'COYOACAN']`` (COYOACAN sin tilde).

    La UI y SQLite local usan ``COYOACÁN``; aquí se normaliza al valor que valida Pydantic.
    """
    raw = (
        _field_to_db(record.get("sede"), False)
        or str(record.get("sede", "")).strip().upper()
    )
    if not raw:
        return ""
    if raw == "AJUSCO":
        return "AJUSCO"
    # Cualquier variante con tilde o ya sin ella → COYOACAN
    if raw.replace("Á", "A") == "COYOACAN":
        return "COYOACAN"
    return raw


def _opt_str_api(value: str | None) -> str | None:
    """Optional[str] del backend: vacío → null (None), no cadena vacía."""
    v = _field_to_db(value, False)
    return v if v else None


def _opt_int_api(value: Any) -> int | None:
    """Optional[int] del backend; convierte tipos numéricos (p. ej. numpy) a int nativo."""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _aspect_mode_for_api(record: dict) -> str:
    """``Literal['FREE', 'SQUARE']`` del backend."""
    am = str(record.get("aspect_mode", "FREE")).strip().upper()
    return am if am in ("FREE", "SQUARE") else "FREE"


def _record_to_insert_payload(record: dict) -> dict[str, Any]:
    """
    Cuerpo JSON para ``POST /registros`` alineado con ``RegistroBase`` (Pydantic en FastAPI).

    No incluye campos de auditoría; el backend toma el usuario del JWT.
    """
    sede = _sede_for_api(record)
    nombre_imagen = (
        _field_to_db(record.get("nombre_imagen"), False)
        or str(record.get("nombre_imagen", "")).strip().upper()
    )
    destinatario_raw = _field_to_db(record.get("destinatario_raw"), True) or ""

    return {
        "sede": sede,
        "nombre_imagen": nombre_imagen,
        "destinatario_raw": destinatario_raw,
        "nombre_o_titulo": _opt_str_api(record.get("nombre_o_titulo")),
        "cargo_dependencia": _opt_str_api(record.get("cargo_dependencia")),
        "direccion": _opt_str_api(record.get("direccion")),
        "colonia": _opt_str_api(record.get("colonia")),
        "municipio_o_alcaldia": _opt_str_api(record.get("municipio_o_alcaldia")),
        "estado": _opt_str_api(record.get("estado")),
        "codigo_postal": _opt_str_api(record.get("codigo_postal")),
        "extras": _opt_str_api(record.get("extras")),
        "contacto": _opt_str_api(record.get("contacto")),
        "indicaciones": _opt_str_api(record.get("indicaciones")),
        "observaciones_ia": _opt_str_api(record.get("observaciones_ia")),
        "crop_x": _opt_int_api(record.get("crop_x")),
        "crop_y": _opt_int_api(record.get("crop_y")),
        "crop_w": _opt_int_api(record.get("crop_w")),
        "crop_h": _opt_int_api(record.get("crop_h")),
        "rotation_deg": _opt_int_api(record.get("rotation_deg")),
        "aspect_mode": _aspect_mode_for_api(record),
    }


def _insert_extraction_api(record: dict) -> int:
    token = get_access_token()
    if not token:
        raise RepositoryApiError("No hay sesión activa. Inicie sesión de nuevo.")

    payload = _record_to_insert_payload(record)
    return create_registro(payload, token)


def insert_extraction(record: dict) -> int:
    """
    Inserta un registro y devuelve el id generado por la API.
    """
    return _insert_extraction_api(record)


def _datetimes_to_api_iso_params(inicio: datetime, fin: datetime) -> tuple[str, str]:
    """Query params ``fecha_inicio`` / ``fecha_fin`` en ISO con ``T`` (segundos sin microsegundos)."""
    a = inicio.replace(microsecond=0)
    b = fin.replace(microsecond=0)
    return (
        a.isoformat(sep="T", timespec="seconds"),
        b.isoformat(sep="T", timespec="seconds"),
    )


def _sede_filter_for_api_query(sede: str | None) -> str | None:
    """
    Valor de query ``sede`` para GET /registros: ``AJUSCO`` | ``COYOACAN`` o None (no filtrar).

    Vacío o desconocido → None (no se envía el parámetro).
    """
    if sede is None:
        return None
    t = str(sede).strip()
    if not t:
        return None
    u = t.upper()
    if u == "AJUSCO":
        return "AJUSCO"
    if u.replace("Á", "A") == "COYOACAN":
        return "COYOACAN"
    return None

def _list_by_date_range_api(desde: datetime, hasta: datetime, sede: str | None) -> list[dict]:
    token = get_access_token()
    if not token:
        raise RepositoryApiError("No hay sesión activa. Inicie sesión de nuevo.")

    fecha_inicio, fecha_fin = _datetimes_to_api_iso_params(desde, hasta)
    params: dict[str, Any] = {
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
    }
    sede_q = _sede_filter_for_api_query(sede)
    if sede_q is not None:
        params["sede"] = sede_q

    return list_registros(params, token)

def list_by_date_range(desde: datetime, hasta: datetime, sede: str | None = None) -> list[dict]:
    """
    Lista registros desde la API entre ``desde`` y ``hasta`` (incluyente), opcionalmente por sede.

    ``sede`` en la UI puede ser ``AJUSCO`` o ``COYOACÁN``; hacia la API se normaliza a
    ``COYOACAN`` sin tilde.
    """
    return _list_by_date_range_api(desde, hasta, sede)
