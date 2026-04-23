# [MODIFICADO] Persistencia vía FastAPI (POST/GET /registros + JWT); SQLite solo con
# OCR_USE_SQLITE_REPOSITORY=1 (pytest).

"""Repositorio de extracciones: API FastAPI (JWT) en ejecución normal; SQLite/MySQL solo en tests."""
from __future__ import annotations

import contextlib
import os
import sqlite3
from datetime import datetime, time
from pathlib import Path
from typing import Any, Iterator

import httpx

import app.config as app_config
from app.config import API_TIMEOUT_SECONDS, DB_PATH, DATA_DIR, REGISTROS_ENDPOINT, api_abs_url

from app.core.auth_client import get_access_token


class RepositoryApiError(Exception):
    """Fallo al crear registro por HTTP (red, 4xx/5xx, cuerpo sin id). Mensaje para la UI."""

# Raíz del proyecto (…/ExtractorOcrImagenes)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Migración SQLite: renombrar columnas antiguas campos_*.
_LEGACY_CAMPOS_TO_COLUMN = [
    ("campos_nombre_o_titulo", "nombre_o_titulo"),
    ("campos_cargo_dependencia", "cargo_dependencia"),
    ("campos_direccion", "direccion"),
    ("campos_colonia", "colonia"),
    ("campos_municipio_o_alcaldia", "municipio_o_alcaldia"),
    ("campos_estado", "estado"),
    ("campos_codigo_postal", "codigo_postal"),
    ("campos_extras", "extras"),
    ("campos_contacto", "contacto"),
    ("campos_indicaciones", "indicaciones"),
]


def _ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


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


def _placeholder(engine: str) -> str:
    return "%s" if engine == "mysql" else "?"


def _repository_use_local_sqlite() -> bool:
    """
    Si es verdadero, ``insert_extraction`` / list usan BD local (solo tests automatizados).

    En ejecución normal no definir ``OCR_USE_SQLITE_REPOSITORY`` para usar la API.
    """
    return os.getenv("OCR_USE_SQLITE_REPOSITORY", "").lower() in ("1", "true", "yes")


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


def _http_error_detail(response: httpx.Response) -> str:
    try:
        data = response.json()
        if isinstance(data, dict):
            d = data.get("detail")
            if isinstance(d, str):
                return d
            if isinstance(d, list):
                return "; ".join(
                    str(x.get("msg", x)) if isinstance(x, dict) else str(x) for x in d
                )
    except ValueError:
        pass
    text = (response.text or "").strip()
    return text[:500] if text else "(sin detalle)"


def _coerce_positive_id(value: Any) -> int | None:
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, str) and value.isdigit():
        i = int(value)
        return i if i > 0 else None
    return None


def _parse_new_id(body: object) -> int | None:
    """Interpreta respuesta típica FastAPI / Pydantic: id en raíz o bajo registro/data."""
    if not isinstance(body, dict):
        return None
    for key in ("id", "registro_id"):
        rid = _coerce_positive_id(body.get(key))
        if rid is not None:
            return rid
    nested = body.get("registro")
    if not isinstance(nested, dict):
        nested = body.get("data")
    if isinstance(nested, dict):
        for key in ("id", "registro_id"):
            rid = _coerce_positive_id(nested.get(key))
            if rid is not None:
                return rid
    return None


def _insert_extraction_api(record: dict) -> int:
    token = get_access_token()
    if not token:
        raise RepositoryApiError("No hay sesión activa. Inicie sesión de nuevo.")

    url = api_abs_url(REGISTROS_ENDPOINT)
    payload = _record_to_insert_payload(record)
    headers = {"Authorization": f"Bearer {token}"}

    try:
        with httpx.Client(timeout=API_TIMEOUT_SECONDS) as client:
            response = client.post(url, json=payload, headers=headers)
    except httpx.TimeoutException as e:
        raise RepositoryApiError("Tiempo de espera al guardar el registro.") from e
    except httpx.RequestError as e:
        raise RepositoryApiError(f"No se pudo conectar con el servidor: {e}") from e

    if response.status_code == 401:
        raise RepositoryApiError(
            "Sesión caducada o no autorizado. Vuelva a iniciar sesión."
        )

    if response.status_code >= 400:
        raise RepositoryApiError(
            f"No se pudo guardar (código {response.status_code}): "
            f"{_http_error_detail(response)}"
        )

    try:
        body = response.json() if response.content else {}
    except ValueError as e:
        raise RepositoryApiError("La respuesta del servidor no es JSON válido.") from e

    rid = _parse_new_id(body)
    if rid is None:
        raise RepositoryApiError(
            "El servidor no devolvió el identificador del registro (campo id)."
        )
    return rid


def create_tables_sqlite(conn: sqlite3.Connection) -> None:
    """Crea las tablas en SQLite."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS extractions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sede TEXT NOT NULL CHECK (sede IN ('AJUSCO', 'COYOACÁN')),
            nombre_imagen TEXT NOT NULL,
            destinatario_raw TEXT NOT NULL,
            nombre_o_titulo TEXT,
            cargo_dependencia TEXT,
            direccion TEXT,
            colonia TEXT,
            municipio_o_alcaldia TEXT,
            estado TEXT,
            codigo_postal TEXT,
            extras TEXT,
            contacto TEXT,
            indicaciones TEXT,
            observaciones_ia TEXT,
            crop_x INTEGER,
            crop_y INTEGER,
            crop_w INTEGER,
            crop_h INTEGER,
            rotation_deg INTEGER,
            aspect_mode TEXT CHECK (aspect_mode IN ('FREE', 'SQUARE')),
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_extractions_created_at ON extractions(created_at)"
    )
    conn.commit()


def migrate_extractions_legacy_columns_sqlite(conn: sqlite3.Connection) -> None:
    """Renombra columnas campos_* en SQLite existente (SQLite 3.25+)."""
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='extractions'"
    )
    if not cur.fetchone():
        return
    cur = conn.execute("PRAGMA table_info(extractions)")
    cols = {row[1] for row in cur.fetchall()}
    for old, new in _LEGACY_CAMPOS_TO_COLUMN:
        if old in cols and new not in cols:
            conn.execute(f'ALTER TABLE extractions RENAME COLUMN "{old}" TO "{new}"')
            cols.remove(old)
            cols.add(new)
    conn.commit()


def _mysql_schema_statements() -> list[str]:
    path = _PROJECT_ROOT / "sql" / "schema_mysql.sql"
    raw = path.read_text(encoding="utf-8")
    stmts: list[str] = []
    for chunk in raw.split(";"):
        lines = []
        for line in chunk.splitlines():
            line = line.strip()
            if not line or line.startswith("--"):
                continue
            lines.append(line)
        s = " ".join(lines).strip()
        if s:
            stmts.append(s + ";")
    return stmts


def ensure_mysql_tables(conn) -> None:
    """Ejecuta sql/schema_mysql.sql (CREATE IF NOT EXISTS)."""
    cur = conn.cursor()
    for stmt in _mysql_schema_statements():
        cur.execute(stmt)
    conn.commit()
    cur.close()


@contextlib.contextmanager
def get_connection() -> Iterator[tuple[object, str]]:
    """
    Context manager: (connection, engine) donde engine es ``sqlite`` o ``mysql``.
    Cierra la conexión al salir.
    """
    if app_config.is_mysql():
        import pymysql

        cfg = app_config.get_mysql_config()
        if not cfg.get("user"):
            raise RuntimeError(
                "DB_ENGINE=mysql requiere DB_USER (y demás variables). Ver .env.example."
            )
        conn = pymysql.connect(
            host=cfg["host"],
            port=cfg["port"],
            user=cfg["user"],
            password=cfg["password"],
            database=cfg["database"],
            charset=cfg["charset"],
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False,
        )
        try:
            ensure_mysql_tables(conn)
            yield conn, "mysql"
        finally:
            conn.close()
        return

    _ensure_data_dir()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    create_tables_sqlite(conn)
    migrate_extractions_legacy_columns_sqlite(conn)
    try:
        yield conn, "sqlite"
    finally:
        conn.close()


def insert_extraction(record: dict) -> int:
    """
    Inserta un registro y devuelve el id.

    En ejecución normal: ``POST`` al backend con JWT (sin ``created_by`` en el cuerpo).
    Con ``OCR_USE_SQLITE_REPOSITORY=1`` (tests): INSERT en SQLite/MySQL local.
    """
    if _repository_use_local_sqlite():
        return _insert_extraction_local(record)
    return _insert_extraction_api(record)


def _insert_extraction_local(record: dict) -> int:
    """INSERT en SQLite o MySQL (solo tests o entorno explícito)."""
    params = (
        _field_to_db(record.get("sede"), False) or record.get("sede", "").upper(),
        _field_to_db(record.get("nombre_imagen"), False)
        or record.get("nombre_imagen", "").upper(),
        _field_to_db(record.get("destinatario_raw"), True) or "",
        _field_to_db(record.get("nombre_o_titulo")),
        _field_to_db(record.get("cargo_dependencia")),
        _field_to_db(record.get("direccion")),
        _field_to_db(record.get("colonia")),
        _field_to_db(record.get("municipio_o_alcaldia")),
        _field_to_db(record.get("estado")),
        _field_to_db(record.get("codigo_postal")),
        _field_to_db(record.get("extras")),
        _field_to_db(record.get("contacto")),
        _field_to_db(record.get("indicaciones")),
        _field_to_db(record.get("observaciones_ia")),
        record.get("crop_x"),
        record.get("crop_y"),
        record.get("crop_w"),
        record.get("crop_h"),
        record.get("rotation_deg"),
        record.get("aspect_mode", "FREE"),
    )

    with get_connection() as (conn, engine):
        ph = _placeholder(engine)
        sql = f"""
            INSERT INTO extractions (
                sede, nombre_imagen, destinatario_raw,
                nombre_o_titulo, cargo_dependencia, direccion,
                colonia, municipio_o_alcaldia, estado,
                codigo_postal, extras, contacto, indicaciones,
                observaciones_ia, crop_x, crop_y, crop_w, crop_h, rotation_deg, aspect_mode
            ) VALUES ({",".join([ph] * 20)})
            """
        if engine == "mysql":
            cur = conn.cursor()
            cur.execute(sql, params)
            conn.commit()
            last = cur.lastrowid
            cur.close()
            return int(last)
        cur = conn.execute(sql, params)
        conn.commit()
        return int(cur.lastrowid)


def _datetimes_to_api_iso_params(inicio: datetime, fin: datetime) -> tuple[str, str]:
    """Query params ``fecha_inicio`` / ``fecha_fin`` en ISO con ``T`` (segundos sin microsegundos)."""
    a = inicio.replace(microsecond=0)
    b = fin.replace(microsecond=0)
    return (
        a.isoformat(sep="T", timespec="seconds"),
        b.isoformat(sep="T", timespec="seconds"),
    )


def _local_datetime_sql_value(dt: datetime) -> str:
    """Literal comparable con ``created_at`` en SQLite/MySQL."""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


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


def _sede_filter_for_local_column(sede: str | None) -> str | None:
    """Valor exacto en ``extractions.sede`` (SQLite usa COYOACÁN con tilde)."""
    q = _sede_filter_for_api_query(sede)
    if q is None:
        return None
    if q == "COYOACAN":
        return "COYOACÁN"
    return q


def _parse_registros_list_json(data: Any) -> list[dict]:
    """Lista en raíz o bajo items/registros/data/results."""
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        for key in ("items", "registros", "data", "results"):
            inner = data.get(key)
            if isinstance(inner, list):
                return [x for x in inner if isinstance(x, dict)]
    raise RepositoryApiError(
        "La respuesta del servidor no es una lista de registros reconocible."
    )


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

    url = api_abs_url(REGISTROS_ENDPOINT)
    headers = {"Authorization": f"Bearer {token}"}

    try:
        with httpx.Client(timeout=API_TIMEOUT_SECONDS) as client:
            response = client.get(url, headers=headers, params=params)
    except httpx.TimeoutException as e:
        raise RepositoryApiError("Tiempo de espera al consultar registros.") from e
    except httpx.RequestError as e:
        raise RepositoryApiError(f"No se pudo conectar con el servidor: {e}") from e

    if response.status_code == 401:
        raise RepositoryApiError(
            "Sesión caducada o no autorizado. Vuelva a iniciar sesión."
        )

    if response.status_code >= 400:
        raise RepositoryApiError(
            f"No se pudieron obtener registros (código {response.status_code}): "
            f"{_http_error_detail(response)}"
        )

    try:
        payload = response.json()
    except ValueError as e:
        raise RepositoryApiError("La respuesta del servidor no es JSON válido.") from e

    rows = _parse_registros_list_json(payload)
    return rows


def _list_by_date_range_local(desde: datetime, hasta: datetime, sede: str | None) -> list[dict]:
    """SELECT local por rango de fecha-hora; ``sede`` opcional filtra por columna."""
    sede_val = _sede_filter_for_local_column(sede)
    d1 = _local_datetime_sql_value(desde)
    d2 = _local_datetime_sql_value(hasta)
    with get_connection() as (conn, engine):
        ph = _placeholder(engine)
        extra_sql = ""
        extra_params: list[Any] = []
        if sede_val is not None:
            extra_sql = f" AND sede = {ph}"
            extra_params = [sede_val]

        if engine == "mysql":
            sql = f"""
            SELECT * FROM extractions
            WHERE created_at >= {ph} AND created_at <= {ph}
            {extra_sql}
            ORDER BY created_at
            """
            params = (d1, d2, *extra_params)
        else:
            sql = f"""
            SELECT * FROM extractions
            WHERE created_at >= {ph} AND created_at <= {ph}
            {extra_sql}
            ORDER BY created_at
            """
            params = (d1, d2, *extra_params)

        if engine == "mysql":
            cur = conn.cursor()
            cur.execute(sql, params)
            rows = cur.fetchall()
            cur.close()
            return [dict(r) for r in rows]
        cur = conn.execute(sql, params)
        rows = cur.fetchall()
        return [dict(row) for row in rows]


def list_by_date_range(
    desde: datetime,
    hasta: datetime,
    sede: str | None = None,
) -> list[dict]:
    """
    Lista registros entre ``desde`` y ``hasta`` (incluyente en tiempo), opcionalmente por sede.

    En ejecución normal: ``GET /registros`` con ``fecha_inicio`` / ``fecha_fin`` en ISO y
    ``sede`` solo si aplica. El usuario lo determina el JWT en el servidor.

    ``sede`` en la UI puede ser ``AJUSCO`` o ``COYOACÁN``; hacia la API se normaliza a
    ``COYOACAN`` sin tilde.
    """
    if _repository_use_local_sqlite():
        return _list_by_date_range_local(desde, hasta, sede)
    return _list_by_date_range_api(desde, hasta, sede)
