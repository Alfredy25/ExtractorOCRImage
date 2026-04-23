# [MODIFICADO] Normalización de registros (GET /registros) antes de exportar; fechas ISO.

"""Exportación a CSV y Excel."""
from __future__ import annotations

import csv
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from app.config import EXPORT_DIR

# Campos que ``_records_to_rows`` lee de cada dict (contrato API / SQLite).
_EXPORT_SOURCE_KEYS = (
    "created_at",
    "indicaciones",
    "nombre_o_titulo",
    "cargo_dependencia",
    "direccion",
    "colonia",
    "municipio_o_alcaldia",
    "estado",
    "codigo_postal",
    "contacto",
    "extras",
    "observaciones_ia",
    "nombre_imagen",
    "destinatario_raw",
)

EXPORT_COLUMNS = [
    "fecha",
    "indicaciones",
    "nombre_o_titulo",
    "cargo_dependencia",
    "direccion",
    "colonia",
    "municipio_o_alcaldia",
    "estado",
    "codigo_postal",
    "contacto",
    "extras",
    "observaciones_ia",
    "imagen",
    "destinatario_raw",
]


def normalize_registro_for_export(reg: dict) -> dict:
    """
    Garantiza las claves que usa la exportación (respuesta GET /registros o SQLite).

    No elimina ``id``, ``created_by``, etc.: columnas extra no molestan a pandas/CSV.
    """
    if not isinstance(reg, dict):
        return {}
    out = dict(reg)
    for k in _EXPORT_SOURCE_KEYS:
        if k not in out:
            out[k] = None
    return out


def normalize_registros_for_export(records: list[dict]) -> list[dict]:
    """Lista lista para ``export_csv`` / ``export_excel`` / ``_records_to_rows``."""
    return [normalize_registro_for_export(r) for r in records if isinstance(r, dict)]


def _fecha_from_created_at(created: Any) -> str:
    """
    ``created_at`` del API suele ser ISO ``2026-04-22T17:35:47`` o con espacio;
    la hoja muestra ``dd-mm-aaaa``.
    """
    if created is None:
        return ""
    if isinstance(created, datetime):
        return created.date().strftime("%d-%m-%Y")
    if type(created) is date:
        return created.strftime("%d-%m-%Y")
    if isinstance(created, str):
        s = created.strip()
        if not s:
            return ""
        if len(s) >= 10 and s[4] == "-" and s[7] == "-":
            try:
                return date.fromisoformat(s[:10]).strftime("%d-%m-%Y")
            except ValueError:
                pass
        return s[:10] if len(s) >= 10 else s
    return str(created)[:10] if created else ""


def _records_to_rows(records: list[dict]) -> list[dict]:
    """Convierte registros de BD a filas para exportar (no reconvierte a mayúsculas)."""
    rows = []
    for r in records:
        created = r.get("created_at")
        fecha = _fecha_from_created_at(created)
        rows.append({
            "fecha": fecha,
            "indicaciones": r.get("indicaciones") or "",
            "nombre_o_titulo": r.get("nombre_o_titulo") or "",
            "cargo_dependencia": r.get("cargo_dependencia") or "",
            "direccion": r.get("direccion") or "",
            "colonia": r.get("colonia") or "",
            "municipio_o_alcaldia": r.get("municipio_o_alcaldia") or "",
            "estado": r.get("estado") or "",
            "codigo_postal": r.get("codigo_postal") or "",
            "contacto": r.get("contacto") or "",
            "extras": r.get("extras") or "",
            "observaciones_ia": r.get("observaciones_ia") or "",
            "imagen": r.get("nombre_imagen") or "",
            "destinatario_raw": r.get("destinatario_raw") or "",
        })
    return rows


def export_csv(records: list[dict], path: Path) -> None:
    """Exporta a CSV con UTF-8 BOM y separador ','."""
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = _records_to_rows(normalize_registros_for_export(records))
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=EXPORT_COLUMNS)
        w.writeheader()
        w.writerows(rows)


def export_excel(records: list[dict], path: Path) -> None:
    """Exporta a Excel con openpyxl."""
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = _records_to_rows(normalize_registros_for_export(records))
    df = pd.DataFrame(rows, columns=EXPORT_COLUMNS)
    df.to_excel(path, index=False, engine="openpyxl")


def suggested_filename(ext: str = "xlsx") -> str:
    """Nombre sugerido: procesados_DD-MM-YYYY.ext."""
    today = date.today()
    return f"procesados_{today.strftime('%d-%m-%Y')}.{ext}"
