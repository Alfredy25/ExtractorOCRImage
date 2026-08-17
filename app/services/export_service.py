# [MODIFICADO] Normalización de registros (GET /registros) antes de exportar; fechas ISO.

"""Exportación a CSV y Excel."""
from __future__ import annotations

import csv
from datetime import date, datetime
from pathlib import Path
from typing import Any
from app.models.shipping import ShippingDto
import pandas as pd
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

from app.config import EXPORT_DIR

# Campos que ``_records_to_rows`` lee de cada dict (contrato API).
_EXPORT_SOURCE_KEYS = (
    "created_at",
    "indicaciones",
    "nombre_titulo",
    "cargo_dependencia",
    "direccion",
    "colonia",
    "municipio_alcaldia",
    "estado",
    "codigo_postal",
    "numero_volante",
    "contacto",
    "extras",
    "observaciones_ia",
    "nombre_imagen",
    "destinatario_raw",
)

EXPORT_COLUMNS = [
    "fecha",
    "indicaciones",
    "nombre_titulo",
    "cargo_dependencia",
    "direccion",
    "colonia",
    "municipio_alcaldia",
    "estado",
    "codigo_postal",
    "numero_volante",
    "contacto",
    "extras",
    "observaciones_ia",
    "imagen",
    "destinatario_raw",
]


def normalize_registro_for_export(reg: dict) -> dict:
    """
    Garantiza las claves que usa la exportación (respuesta GET /registros).

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
    la hoja muestra ``dd-mm-aaaa HH:MM``.
    """
    if created is None:
        return ""
    if isinstance(created, datetime):
        return created.strftime("%d-%m-%Y %H:%M")
    if type(created) is date:
        return created.strftime("%d-%m-%Y %H:%M")
    if isinstance(created, str):
        s = created.strip()
        if not s:
            return ""
        if len(s) >= 10 and s[4] == "-" and s[7] == "-":
            try:
                parsed = datetime.fromisoformat(s.replace("Z", "+00:00"))
                return parsed.strftime("%d-%m-%Y %H:%M")
            except ValueError:
                pass
        return s[:16] if len(s) >= 16 else s
    return str(created)[:16] if created else ""


def _records_to_rows(records: list[dict]) -> list[dict]:
    """Convierte registros de BD a filas para exportar (no reconvierte a mayúsculas)."""
    rows = []
    for r in records:
        created = r.get("created_at")
        fecha = _fecha_from_created_at(created)
        rows.append({
            "fecha": fecha,
            "indicaciones": r.get("indicaciones") or "",
            "nombre_titulo": r.get("nombre_titulo") or "",
            "cargo_dependencia": r.get("cargo_dependencia") or "",
            "direccion": r.get("direccion") or "",
            "colonia": r.get("colonia") or "",
            "municipio_alcaldia": r.get("municipio_alcaldia") or "",
            "estado": r.get("estado") or "",
            "codigo_postal": r.get("codigo_postal") or "",
            "numero_volante": r.get("numero_volante") or "",
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

EXPORT_COLUMNS_SHIPMENTS = [
    "ID_CLIENTE_DEST",
    "NOMBRE",
    "RFC",
    "PAIS",
    "ESTADO",
    "CIUDAD",
    "CALLE",
    "NUMERO",
    "COLONIA",
    "CP",
    "EMAIL",
    "TELEFONO",
    "REFERENCIA_DOMICILIO",
    "CANTIDAD",
    "CODIGO_BULTO",
    "CONTENIDO",
    "TIPO_TARIFA",
    "PESO",
    "VOLUMEN",
    "LARGO",
    "ANCHO",
    "ALTO",
    "TIPO_ENTREGA",
    "FORMA_PAGO",
    "ACUSE",
    "COD",
    "VALOR_DECLARADO",
    "COBERTURA",
    "COMENTARIOS",
    "REFERENCIA",
    "AGENTE_ADUANAL",
    "PEDIMENTO",
    "CENTRO_COSTO",
    "CVE_MENSAJE",
    "TIPO_MENSAJE",
    "DES_MENSAJE",
    "RASTREO",
    "GUIA",
    "IMPORTE",
    "LINK_PDF",
    "CANTIDAD_RASTREOS",
    "TIPO_SERVICIO",
    "ID_PRODUCTO"]

def _shipments_to_rows(shipments: list[ShippingDto]) -> list[dict: any]:
    """Convierte registros de BD a filas para exportar (no reconvierte a mayúsculas)."""
    rows = []
    for shipment in shipments:
        rows.append({
            "ID_CLIENTE_DEST": str(shipment.id_folio).zfill(7),
            "NOMBRE": shipment.name_receiver,
            "RFC": shipment.rfc,
            "PAIS": shipment.country,
            "ESTADO": shipment.state,
            "CIUDAD": shipment.city,
            "CALLE": shipment.street,
            "NUMERO": shipment.num_street,
            "COLONIA": shipment.colony,
            "CP": shipment.postal_code,
            "EMAIL": shipment.email,
            "TELEFONO": shipment.phone,
            "REFERENCIA_DOMICILIO": shipment.address_reference,
            "CANTIDAD": shipment.quantity,
            "CODIGO_BULTO": shipment.package_code,
            "CONTENIDO": shipment.content,
            "TIPO_TARIFA": "",
            "PESO": shipment.weight,
            "VOLUMEN": 0,
            "LARGO": shipment.length,
            "ANCHO": shipment.width,
            "ALTO": shipment.height,
            "TIPO_ENTREGA": 2,
            "FORMA_PAGO": "PAID",
            "ACUSE": "N",
            "COD": 0,
            "VALOR_DECLARADO": 0,
            "COBERTURA": "N",
            "COMENTARIOS": shipment.comments,
            "REFERENCIA": "ASF",
            "AGENTE_ADUANAL": "",
            "PEDIMENTO": "",
            "CENTRO_COSTO": "",
            "CVE_MENSAJE": "",
            "TIPO_MENSAJE": "",
            "DES_MENSAJE":"",
            "RASTREO": "",
            "GUIA": "",
            "IMPORTE": "",
            "LINK_PDF": "",
            "CANTIDAD_RASTREOS": "",
            "TIPO_SERVICIO": "",
            "ID_PRODUCTO": "",
        })
    return rows

def filename_shipments(ext: str = "xlsx") -> str:
    """Nombre sugerido: envios_DD-MM-YYYY.ext."""
    today = date.today()
    return f"envios_{today.strftime('%d-%m-%Y')}.{ext}"


def export_shipments_excel(shipments: list[ShippingDto], path: Path) -> bool:
    """Exporta a Excel con openpyxl."""
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = _shipments_to_rows(shipments)
    df = pd.DataFrame(rows, columns=EXPORT_COLUMNS_SHIPMENTS)
    return save_to_excel(df, path)


def save_to_excel(df: pd.DataFrame, path: Path) -> bool:
    """Guarda el DataFrame en un archivo Excel."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Envios"
    border = Border(left=Side(style="thin"), right=Side(style="thin"), 
                        top=Side(style="thin"), bottom=Side(style="thin"))

    COLUMN_WIDTHS = {
        "ID_CLIENTE_DEST": 15,
        "NOMBRE": 40,
        "RFC": 16,
        "PAIS": 12,
        "ESTADO": 20,
        "CIUDAD": 25,
        "CALLE": 30,
        "NUMERO": 15,
        "COLONIA": 30,
        "CP": 12,
        "EMAIL": 20,
        "TELEFONO": 20,
        "REFERENCIA_DOMICILIO": 20,
        "CANTIDAD": 10,
        "CODIGO_BULTO": 10,
        "CONTENIDO": 20,
        "TIPO_TARIFA": 10,
        "PESO": 10,
        "VOLUMEN": 10,
        "LARGO": 10,
        "ANCHO": 10,
        "ALTO": 10,
        "TIPO_ENTREGA": 10,
        "FORMA_PAGO": 10,
        "ACUSE": 10,
        "COD": 10,
        "VALOR_DECLARADO": 10,
        "COBERTURA": 10,
        "COMENTARIOS": 30,
        "REFERENCIA": 10,
        "AGENTE_ADUANAL": 10,
        "PEDIMENTO": 10,
        "CENTRO_COSTO": 10,
        "CVE_MENSAJE": 10,
        "TIPO_MENSAJE": 10,
        "DES_MENSAJE": 10,
        "RASTREO": 10,
        "GUIA": 10,
        "IMPORTE": 10,
        "LINK_PDF": 10,
        "CANTIDAD_RASTREOS": 10,
        "TIPO_SERVICIO": 10,
        "ID_PRODUCTO": 10    
        }


    # Escribir DataFrame completo
    for row in dataframe_to_rows(df, index=False, header=True):
        ws.append(row)
    
    # Formato de encabezados
    for col_num, cell in enumerate(ws[1], 1):
        cell.font = Font(bold=False, color="FFFFFF", size=11, name="Aptos Narrow")
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = border
        if col_num == 1:
            cell.fill = PatternFill(start_color="E97132", end_color="E97132", fill_type="solid")
        elif col_num > 1 and col_num <= 10:
            cell.fill = PatternFill(start_color="104861", end_color="104861", fill_type="solid")
        elif col_num > 10 and col_num <= 13:
            cell.fill = PatternFill(start_color="196B24", end_color="196B24", fill_type="solid")
        elif col_num > 13 and col_num <= 22:
            cell.fill = PatternFill(start_color="00B0F0", end_color="00B0F0", fill_type="solid")
        elif col_num > 22 and col_num <= 28:
            cell.fill = PatternFill(start_color="8064A2", end_color="8064A2", fill_type="solid")
        elif col_num > 28 and col_num <= 33:
            cell.fill = PatternFill(start_color="002060", end_color="002060", fill_type="solid")
        elif col_num > 33 and col_num <= 40:
            cell.fill = PatternFill(start_color="C0504D", end_color="C0504D", fill_type="solid")
        elif col_num > 40 and col_num <= 43:
            cell.fill = PatternFill(start_color="002060", end_color="002060", fill_type="solid")

    
    # Formato de datos
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=1, max_col=ws.max_column):
        for cell in row:
            cell.font = Font(bold=False, size=11, name="Aptos Narrow")
            cell.alignment = Alignment(horizontal="left", vertical="center")
            cell.border = border
    
    # Formatear ancho de columnas
    for col_idx, header in enumerate(EXPORT_COLUMNS_SHIPMENTS, start=1):
        letter = get_column_letter(col_idx)
        ws.column_dimensions[letter].width = COLUMN_WIDTHS.get(header, 10)

    
    wb.save(path)
    wb.close()
    return True
    
    


