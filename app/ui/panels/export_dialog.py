"""Diálogo de exportación: rango de fecha y hora por separado, sede opcional, Descargas por defecto."""
from datetime import datetime, time
from pathlib import Path

from PySide6.QtCore import QDate, QTime, QStandardPaths
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QDateEdit,
    QTimeEdit,
    QComboBox,
    QPushButton,
    QFileDialog,
    QMessageBox,
)

from app.config import SEDES
from app.core.exporters import export_csv, export_excel, suggested_filename
from app.core.repository import list_by_date_range


def _downloads_folder() -> Path:
    """Carpeta Descargas del usuario (nombre localizado vía Qt)."""
    loc = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.DownloadLocation
    )
    if loc:
        return Path(loc)
    return Path.home() / "Downloads"


class ExportDialog(QDialog):
    """Exportar registros del API (o SQLite en tests) a Excel/CSV."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Exportar registros")
        self._setup_ui()

    @staticmethod
    def _qtime_to_pytime(qt: QTime) -> time:
        return time(qt.hour(), qt.minute(), qt.second())

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Desde — fecha (dd/mm/aaaa):"))
        row_df = QHBoxLayout()
        self._date_from = QDateEdit()
        self._date_from.setCalendarPopup(True)
        self._date_from.setDisplayFormat("dd/MM/yyyy")
        self._date_from.setDate(QDate.currentDate().addMonths(-1))
        row_df.addWidget(self._date_from)
        layout.addLayout(row_df)

        layout.addWidget(QLabel("Desde — hora (hh:mm, 24 h):"))
        row_tf = QHBoxLayout()
        self._time_from = QTimeEdit()
        self._time_from.setDisplayFormat("HH:mm")
        self._time_from.setTime(QTime(0, 0))
        row_tf.addWidget(self._time_from)
        layout.addLayout(row_tf)

        layout.addWidget(QLabel("Hasta — fecha (dd/mm/aaaa):"))
        row_dt = QHBoxLayout()
        self._date_to = QDateEdit()
        self._date_to.setCalendarPopup(True)
        self._date_to.setDisplayFormat("dd/MM/yyyy")
        self._date_to.setDate(QDate.currentDate())
        row_dt.addWidget(self._date_to)
        layout.addLayout(row_dt)

        layout.addWidget(QLabel("Hasta — hora (hh:mm, 24 h):"))
        row_tt = QHBoxLayout()
        self._time_to = QTimeEdit()
        self._time_to.setDisplayFormat("HH:mm")
        self._time_to.setTime(QTime(23, 59))
        row_tt.addWidget(self._time_to)
        layout.addLayout(row_tt)

        layout.addWidget(QLabel("Sede (opcional):"))
        self._sede = QComboBox()
        self._sede.addItem("Todas las sedes", None)
        for sede in SEDES:
            self._sede.addItem(sede, sede)
        layout.addWidget(self._sede)

        layout.addWidget(QLabel("Formato:"))
        self._format = QComboBox()
        self._format.addItems(["Excel (.xlsx)", "CSV (.csv)"])
        layout.addWidget(self._format)

        btn_layout = QHBoxLayout()
        btn_export = QPushButton("Exportar")
        btn_export.clicked.connect(self._do_export)
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_export)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

    def _do_export(self):
        d0 = self._date_from.date().toPython()
        t0 = self._qtime_to_pytime(self._time_from.time())
        d1 = self._date_to.date().toPython()
        t1 = self._qtime_to_pytime(self._time_to.time())

        dt_desde = datetime.combine(d0, t0)
        dt_hasta = datetime.combine(d1, t1)
        if dt_desde > dt_hasta:
            QMessageBox.warning(
                self,
                "Rango inválido",
                "La fecha y hora 'Desde' deben ser anteriores o iguales a 'Hasta'.",
            )
            return

        is_excel = self._format.currentIndex() == 0
        ext = "xlsx" if is_excel else "csv"
        default_name = suggested_filename(ext)
        default_path = str(_downloads_folder() / default_name)

        path_str, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar exportación",
            default_path,
            "Excel (*.xlsx);;CSV (*.csv)" if is_excel else "CSV (*.csv);;Excel (*.xlsx)",
        )
        if not path_str:
            return

        path = Path(path_str)
        sede = self._sede.currentData()
        records = list_by_date_range(dt_desde, dt_hasta, sede)
        if not records:
            sede_txt = self._sede.currentText()
            extra = f"\nSede: {sede_txt}." if sede else ""
            rango = f"{dt_desde:%d/%m/%Y %H:%M} — {dt_hasta:%d/%m/%Y %H:%M}"
            QMessageBox.information(
                self,
                "Sin datos",
                f"No hay registros en el rango:\n{rango}.{extra}",
            )
            return

        try:
            if path.suffix.lower() in (".xlsx",):
                export_excel(records, path)
            else:
                export_csv(records, path)
            QMessageBox.information(
                self,
                "Exportación completada",
                f"Se exportaron {len(records)} registros a:\n{path}",
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudo exportar: {e}",
            )
