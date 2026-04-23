"""Diálogo de exportación por rango de fechas."""
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QDateEdit,
    QComboBox,
    QPushButton,
    QFileDialog,
    QMessageBox,
)
from PySide6.QtCore import QDate

from app.config import EXPORT_DIR, SEDES
from app.core.repository import list_by_date_range
from app.core.exporters import export_csv, export_excel, suggested_filename


class ExportDialog(QDialog):
    """Diálogo para exportar registros por rango de fechas."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Exportar registros")
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        range_layout = QHBoxLayout()
        range_layout.addWidget(QLabel("Desde:"))
        self._date_from = QDateEdit()
        self._date_from.setCalendarPopup(True)
        self._date_from.setDate(QDate.currentDate().addMonths(-1))
        range_layout.addWidget(self._date_from)

        range_layout.addWidget(QLabel("Hasta:"))
        self._date_to = QDateEdit()
        self._date_to.setCalendarPopup(True)
        self._date_to.setDate(QDate.currentDate())
        range_layout.addWidget(self._date_to)
        layout.addLayout(range_layout)

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
        desde = self._date_from.date().toPython()
        hasta = self._date_to.date().toPython()
        if desde > hasta:
            QMessageBox.warning(
                self,
                "Rango inválido",
                "La fecha 'Desde' debe ser anterior o igual a 'Hasta'.",
            )
            return

        is_excel = self._format.currentIndex() == 0
        ext = "xlsx" if is_excel else "csv"
        default_name = suggested_filename(ext)
        default_path = str(Path(EXPORT_DIR).resolve() / default_name) if EXPORT_DIR else ""

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
        records = list_by_date_range(desde, hasta, sede)
        if not records:
            sede_txt = self._sede.currentText()
            extra = f"\nSede: {sede_txt}." if sede else ""
            QMessageBox.information(
                self,
                "Sin datos",
                f"No hay registros entre {desde} y {hasta}.{extra}",
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
