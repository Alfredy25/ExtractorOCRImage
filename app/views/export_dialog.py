"""Diálogo de exportación: rango de fecha y hora por separado, sede opcional, Descargas por defecto."""
from datetime import datetime, time
from pathlib import Path

from PySide6.QtCore import QDate, QStandardPaths, QTime
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QTimeEdit,
    QVBoxLayout,
)

from app.components.theme import SPACE
from app.components.widgets import (
    Card,
    divider,
    icon_label,
    labeled_field,
    section_label,
    subtitle,
    text_button,
)
from app.config import SEDES
from app.services.export_service import export_csv, export_excel, suggested_filename
from app.services.registros_service import (
    RepositoryApiError,
    RepositorySessionExpiredError,
    list_by_date_range,
)
from app.views.session_relogin import prompt_relogin_after_session_expired


def _downloads_folder() -> Path:
    """Carpeta Descargas del usuario (nombre localizado vía Qt)."""
    loc = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.DownloadLocation
    )
    if loc:
        return Path(loc)
    return Path.home() / "Downloads"


class ExportDialog(QDialog):
    """Exportar registros obtenidos de la API a Excel/CSV."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Exportar registros")
        self.setMinimumWidth(560)
        self._setup_ui()

    @staticmethod
    def _qtime_to_pytime(qt: QTime) -> time:
        return time(qt.hour(), qt.minute(), qt.second())

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACE["lg"], SPACE["lg"], SPACE["lg"], SPACE["lg"])
        layout.setSpacing(SPACE["md"])

        title = QLabel("Exportar registros")
        title.setProperty("role", "headline")
        layout.addWidget(title)
        layout.addWidget(
            subtitle("Selecciona el rango a consultar en el backend y el formato de salida.")
        )

        layout.addWidget(self._build_range_card())
        layout.addWidget(self._build_options_card())
        layout.addStretch(1)
        layout.addWidget(divider())
        layout.addLayout(self._build_actions())

    def _build_range_card(self) -> Card:
        card = Card("Rango de consulta", "calendar_month")

        grid = QGridLayout()
        grid.setHorizontalSpacing(SPACE["md"])
        grid.setVerticalSpacing(SPACE["sm"])

        self._date_from = QDateEdit()
        self._date_from.setCalendarPopup(True)
        self._date_from.setDisplayFormat("dd/MM/yyyy")
        self._date_from.setDate(QDate.currentDate().addMonths(-1))
        grid.addWidget(labeled_field("Desde — fecha (dd/mm/aaaa)", self._date_from, mono=True), 0, 0)

        self._time_from = QTimeEdit()
        self._time_from.setDisplayFormat("HH:mm")
        self._time_from.setTime(QTime(0, 0))
        grid.addWidget(labeled_field("Desde — hora (24 h)", self._time_from, mono=True), 0, 1)

        self._date_to = QDateEdit()
        self._date_to.setCalendarPopup(True)
        self._date_to.setDisplayFormat("dd/MM/yyyy")
        self._date_to.setDate(QDate.currentDate())
        grid.addWidget(labeled_field("Hasta — fecha (dd/mm/aaaa)", self._date_to, mono=True), 1, 0)

        self._time_to = QTimeEdit()
        self._time_to.setDisplayFormat("HH:mm")
        self._time_to.setTime(QTime(23, 59))
        grid.addWidget(labeled_field("Hasta — hora (24 h)", self._time_to, mono=True), 1, 1)

        card.body.addLayout(grid)
        return card

    def _build_options_card(self) -> Card:
        card = Card("Filtros y formato", "filter_alt")

        row = QHBoxLayout()
        row.setSpacing(SPACE["md"])

        self._sede = QComboBox()
        self._sede.addItem("Todas las sedes", None)
        for sede in SEDES:
            self._sede.addItem(sede, sede)
        row.addWidget(labeled_field("Sede (opcional)", self._sede), 1)

        self._format = QComboBox()
        self._format.addItems(["Excel (.xlsx)", "CSV (.csv)"])
        row.addWidget(labeled_field("Formato", self._format), 1)

        card.body.addLayout(row)

        hint = QHBoxLayout()
        hint.setSpacing(SPACE["xs"] + 2)
        hint.addWidget(icon_label("info", 14, role="mutedIcon"))
        hint.addWidget(section_label("Se guardará en Descargas por defecto"))
        hint.addStretch(1)
        card.body.addLayout(hint)
        return card

    def _build_actions(self) -> QHBoxLayout:
        actions = QHBoxLayout()
        actions.setSpacing(SPACE["sm"])
        actions.addStretch(1)

        btn_cancel = text_button("Cancelar", variant="ghost", icon="close")
        btn_cancel.setMinimumHeight(38)
        btn_cancel.clicked.connect(self.reject)
        actions.addWidget(btn_cancel)

        btn_export = text_button("Exportar", variant="primary", icon="download")
        btn_export.setMinimumHeight(38)
        btn_export.setMinimumWidth(150)
        btn_export.clicked.connect(self._do_export)
        actions.addWidget(btn_export)
        return actions

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
        try:
            records = list_by_date_range(dt_desde, dt_hasta, sede)
        except RepositorySessionExpiredError as e:
            prompt_relogin_after_session_expired(
                self, f"No se pudieron obtener registros: {e}"
            )
            return
        except RepositoryApiError as e:
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudieron obtener registros: {e}",
            )
            return

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
