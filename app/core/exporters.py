"""Exportación a CSV y Excel."""
import csv
from datetime import date
from pathlib import Path

import pandas as pd

from app.config import EXPORT_DIR

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


def _records_to_rows(records: list[dict]) -> list[dict]:
    """Convierte registros de BD a filas para exportar (no reconvierte a mayúsculas)."""
    rows = []
    for r in records:
        created = r.get("created_at")
        if isinstance(created, str):
            try:
                dt = date.fromisoformat(created[:10])
                fecha = dt.strftime("%d-%m-%Y")
            except (ValueError, TypeError):
                fecha = str(created)[:10]
        else:
            fecha = str(created)[:10] if created else ""
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
    rows = _records_to_rows(records)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=EXPORT_COLUMNS)
        w.writeheader()
        w.writerows(rows)


def export_excel(records: list[dict], path: Path) -> None:
    """Exporta a Excel con openpyxl."""
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = _records_to_rows(records)
    df = pd.DataFrame(rows, columns=EXPORT_COLUMNS)
    df.to_excel(path, index=False, engine="openpyxl")


def suggested_filename(ext: str = "xlsx") -> str:
    """Nombre sugerido: procesados_DD-MM-YYYY.ext."""
    today = date.today()
    return f"procesados_{today.strftime('%d-%m-%Y')}.{ext}"
