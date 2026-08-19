"""Historial de envíos: consulta por rango, tabla paginada y exportación Excel."""

from __future__ import annotations

from datetime import datetime, time
from pathlib import Path

from PySide6.QtCore import QDate, Qt, QStandardPaths, QTime
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDateEdit,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from app.components.theme import SPACE
from app.components.widgets import (
    divider,
    field_label,
    subtitle,
    text_button,
)
from app.models.shipping import ShippingDto
from app.services.export_service import export_shipments_excel, filename_shipments
from app.services.paquetexpress_service import (
    PaquetexpressServiceError,
    PaquetexpressSessionExpiredError,
    list_shipments_by_date_range,
)
from app.views.session_relogin import prompt_relogin_after_session_expired
from app.views.shipment_window import ShipmentWindow

_PAGE_SIZE = 25

_COLUMNS = [
    "ID envío",
    "Folio",
    "Destinatario",
    "RFC",
    "País",
    "Estado",
    "Ciudad",
    "Colonia",
    "Calle",
    "Número",
    "Código postal",
    "Correo electrónico",
    "Teléfono",
    "Referencia",
    "Cant.",
    "Cód. Paquete",
    "Contenido",
    "Peso (kg)",
    "Dimensiones (LxAxA)",
    "Cobertura",
    "Comentarios",
    "Fecha creación",
]


def _downloads_folder() -> Path:
    """Carpeta Descargas del usuario (nombre localizado vía Qt)."""
    loc = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.DownloadLocation
    )
    if loc:
        return Path(loc)
    return Path.home() / "Downloads"


class ExportShipments(QDialog):
    """Historial de envíos consultados por API, con paginación y export Excel."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ShipmentsHistoryWindow")
        self.setWindowTitle("Historial de Envíos")
        self.resize(1360, 860)
        self.setMinimumSize(1100, 700)
        self.setWindowFlag(Qt.WindowType.WindowMinMaxButtonsHint, True)
        self.setSizeGripEnabled(True)

        self._shipments: list[ShippingDto] = []
        self._page = 0
        self._setup_ui()
        self.setWindowState(self.windowState() | Qt.WindowState.WindowMaximized)

    # --- Construcción --------------------------------------------------

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(SPACE["lg"], SPACE["md"], SPACE["lg"], SPACE["md"])
        root.setSpacing(SPACE["md"])

        root.addWidget(self._build_header())
        root.addWidget(divider())
        root.addWidget(self._build_filters())
        root.addWidget(self._build_table_card(), 1)
        root.addLayout(self._build_actions())

    def _build_header(self) -> QWidget:
        header = QWidget()
        layout = QVBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        title = QLabel("Historial de Envíos")
        title.setProperty("role", "headline")
        layout.addWidget(title)
        layout.addWidget(
            subtitle("Gestión y registro de envíos procesados.")
        )
        return header

    def _build_filters(self) -> QWidget:
        bar = QWidget()
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACE["md"])

        self._date_from = QDateEdit()
        self._date_from.setCalendarPopup(True)
        self._date_from.setDisplayFormat("dd/MM/yyyy")
        self._date_from.setDate(QDate.currentDate().addDays(-1))

        self._time_from = QTimeEdit()
        self._time_from.setDisplayFormat("HH:mm")
        self._time_from.setTime(QTime(8, 0))

        self._date_to = QDateEdit()
        self._date_to.setCalendarPopup(True)
        self._date_to.setDisplayFormat("dd/MM/yyyy")
        self._date_to.setDate(QDate.currentDate())

        self._time_to = QTimeEdit()
        self._time_to.setDisplayFormat("HH:mm")
        now = datetime.now()
        self._time_to.setTime(QTime(now.hour, now.minute))

        layout.addWidget(self._datetime_group("Fecha inicio", self._date_from, self._time_from))
        layout.addWidget(self._datetime_group("Fecha fin", self._date_to, self._time_to))
        layout.addStretch(1)

        btn_consult = text_button("Consultar", variant="ghost", icon="search")
        btn_consult.setObjectName("shipmentsConsultButton")
        btn_consult.setMinimumHeight(38)
        btn_consult.clicked.connect(self._do_consult)
        layout.addWidget(btn_consult)

        btn_export = text_button("Exportar a Excel", variant="primary", icon="table_chart")
        btn_export.setObjectName("shipmentsExportButton")
        btn_export.setMinimumHeight(38)
        btn_export.clicked.connect(self._do_export)
        layout.addWidget(btn_export)
        return bar

    def _datetime_group(self, label: str, date_edit: QDateEdit, time_edit: QTimeEdit) -> QWidget:
        group = QWidget()
        column = QVBoxLayout(group)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(SPACE["xs"])
        column.addWidget(field_label(label))

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(SPACE["sm"])
        date_edit.setMinimumWidth(130)
        time_edit.setMinimumWidth(90)
        row.addWidget(date_edit)
        row.addWidget(time_edit)
        column.addLayout(row)
        return group

    def _build_table_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("ShipmentsTableCard")
        card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tabla = QTableWidget()
        self.tabla.setObjectName("ShipmentsTable")
        self.tabla.setColumnCount(len(_COLUMNS))
        self.tabla.setHorizontalHeaderLabels(_COLUMNS)
        self.tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setShowGrid(False)
        self.tabla.setWordWrap(False)
        self.tabla.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.tabla.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.tabla.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.tabla.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        header = self.tabla.horizontalHeader()
        header.setStretchLastSection(False)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setMinimumSectionSize(80)
        for col in range(len(_COLUMNS)):
            self.tabla.setColumnWidth(col, 130)
        self.tabla.setColumnWidth(2, 220)  # Destinatario
        self.tabla.setColumnWidth(11, 200)  # Correo
        self.tabla.setColumnWidth(16, 180)  # Contenido
        self.tabla.setColumnWidth(20, 200)  # Comentarios

        layout.addWidget(self.tabla, 1)
        layout.addWidget(self._build_pagination_footer())
        self.tabla.itemSelectionChanged.connect(self._update_edit_button)
        return card

    def _build_pagination_footer(self) -> QWidget:
        footer = QFrame()
        footer.setObjectName("ShipmentsTableFooter")
        footer.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QHBoxLayout(footer)
        layout.setContentsMargins(SPACE["md"], SPACE["sm"], SPACE["md"], SPACE["sm"])
        layout.setSpacing(SPACE["sm"])

        self._page_label = QLabel("Mostrando 0 a 0 de 0 registros")
        self._page_label.setObjectName("ShipmentsPageLabel")
        layout.addWidget(self._page_label)
        layout.addStretch(1)

        self._btn_prev = text_button("Anterior", variant="ghost")
        self._btn_prev.setObjectName("shipmentsPrevButton")
        self._btn_prev.setMinimumHeight(32)
        self._btn_prev.clicked.connect(self._go_prev_page)
        layout.addWidget(self._btn_prev)

        self._btn_next = text_button("Siguiente", variant="ghost")
        self._btn_next.setObjectName("shipmentsNextButton")
        self._btn_next.setMinimumHeight(32)
        self._btn_next.clicked.connect(self._go_next_page)
        layout.addWidget(self._btn_next)

        self._update_pagination_controls()
        return footer

    def _build_actions(self) -> QHBoxLayout:
        actions = QHBoxLayout()
        actions.setSpacing(SPACE["sm"])
        actions.addStretch(1)

        self._btn_edit = text_button("Editar", variant="ghost", icon="edit_document")
        self._btn_edit.setObjectName("shipmentsEditButton")
        self._btn_edit.setMinimumHeight(38)
        self._btn_edit.setMinimumWidth(140)
        self._btn_edit.setEnabled(False)
        self._btn_edit.clicked.connect(self._do_edit)
        actions.addWidget(self._btn_edit)

        btn_cancel = text_button("Cancelar", variant="ghost", icon="close")
        btn_cancel.setObjectName("shipmentsCancelButton")
        btn_cancel.setMinimumHeight(38)
        btn_cancel.setMinimumWidth(140)
        btn_cancel.clicked.connect(self.reject)
        actions.addWidget(btn_cancel)

        btn_export = text_button("Exportar a Excel", variant="primary", icon="download")
        btn_export.setObjectName("shipmentsExportFooterButton")
        btn_export.setMinimumHeight(38)
        btn_export.setMinimumWidth(170)
        btn_export.clicked.connect(self._do_export)
        actions.addWidget(btn_export)
        return actions

    # --- Paginación ----------------------------------------------------

    def _total_pages(self) -> int:
        if not self._shipments:
            return 1
        return max(1, (len(self._shipments) + _PAGE_SIZE - 1) // _PAGE_SIZE)

    def _update_pagination_controls(self):
        total = len(self._shipments)
        if total == 0:
            self._page_label.setText("Mostrando 0 a 0 de 0 registros")
            self._btn_prev.setEnabled(False)
            self._btn_next.setEnabled(False)
            return

        start = self._page * _PAGE_SIZE + 1
        end = min(total, (self._page + 1) * _PAGE_SIZE)
        self._page_label.setText(
            f"Mostrando {start} a {end} de {total} registros"
        )
        self._btn_prev.setEnabled(self._page > 0)
        self._btn_next.setEnabled(self._page + 1 < self._total_pages())

    def _go_prev_page(self):
        if self._page <= 0:
            return
        self._page -= 1
        self._render_current_page()

    def _go_next_page(self):
        if self._page + 1 >= self._total_pages():
            return
        self._page += 1
        self._render_current_page()

    def _render_current_page(self):
        start = self._page * _PAGE_SIZE
        end = start + _PAGE_SIZE
        page_items = self._shipments[start:end]
        self._fill_table_rows(page_items)
        self._update_pagination_controls()
        self._update_edit_button()

    # --- Datos ---------------------------------------------------------

    @staticmethod
    def _qtime_to_pytime(qt: QTime) -> time:
        return time(qt.hour(), qt.minute(), qt.second())

    @staticmethod
    def _row_values(shipment: ShippingDto) -> list:
        dimensions = (
            f"{shipment.length}x{shipment.width}x{shipment.height}"
        )
        created = (
            shipment.created_at.strftime("%d/%m/%Y %H:%M")
            if shipment.created_at
            else ""
        )
        return [
            shipment.id_shipping,
            shipment.id_folio,
            shipment.name_receiver,
            shipment.rfc,
            shipment.country,
            shipment.state,
            shipment.city,
            shipment.colony,
            shipment.street,
            shipment.num_street,
            shipment.postal_code,
            str(shipment.email) if shipment.email else "",
            shipment.phone,
            shipment.address_reference,
            shipment.quantity,
            shipment.package_code,
            shipment.content,
            shipment.weight,
            dimensions,
            shipment.coverage_type,
            shipment.comments,
            created,
        ]

    def _fill_table_rows(self, shipments: list[ShippingDto]) -> None:
        self.tabla.clearContents()
        self.tabla.setRowCount(len(shipments))
        for row, shipment in enumerate(shipments):
            for column, value in enumerate(self._row_values(shipment)):
                item = QTableWidgetItem("" if value is None else str(value))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.tabla.setItem(row, column, item)

    def _selected_shipment(self) -> ShippingDto | None:
        selection = self.tabla.selectionModel()
        if selection is None:
            return None
        rows = selection.selectedRows()
        if len(rows) != 1:
            return None
        index = self._page * _PAGE_SIZE + rows[0].row()
        if 0 <= index < len(self._shipments):
            return self._shipments[index]
        return None

    def _update_edit_button(self):
        if not hasattr(self, "_btn_edit"):
            return
        self._btn_edit.setEnabled(self._selected_shipment() is not None)

    def _replace_shipment(self, updated: ShippingDto) -> None:
        selected_row = None
        for index, item in enumerate(self._shipments):
            if item.id_shipping == updated.id_shipping:
                self._shipments[index] = updated
                start = self._page * _PAGE_SIZE
                if start <= index < start + _PAGE_SIZE:
                    selected_row = index - start
                break
        self._render_current_page()
        if selected_row is not None:
            self.tabla.selectRow(selected_row)

    def _do_edit(self):
        shipment = self._selected_shipment()
        if shipment is None:
            return
        dialog = ShipmentWindow.for_edit(shipment, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        updated = dialog.updated_shipment
        if updated is None:
            return
        self._replace_shipment(updated)

    def fill_table(self, shipments: list[ShippingDto]) -> None:
        """Carga todos los envíos y muestra la primera página."""
        self._shipments = list(shipments)
        self._page = 0
        self._render_current_page()

    def _do_consult(self):
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
        try:
            shipments = list_shipments_by_date_range(dt_desde, dt_hasta)
        except PaquetexpressSessionExpiredError as exc:
            prompt_relogin_after_session_expired(
                self, f"No se pudieron obtener envíos: {exc}"
            )
            return
        except PaquetexpressServiceError as exc:
            QMessageBox.critical(self, "Error", f"No se pudieron obtener envíos: {exc}")
            return
        except Exception as exc:
            QMessageBox.critical(
                self, "Error", f"Error inesperado al obtener envíos: {exc}"
            )
            return
        if not shipments:
            self.fill_table([])
            QMessageBox.information(
                self, "Sin datos", "No hay envíos en el rango seleccionado."
            )
            return
        self.fill_table(shipments)

    def _do_export(self):
        if not self._shipments:
            QMessageBox.warning(
                self, "Sin datos", "Consulta primero un rango con envíos."
            )
            return

        default_path = str(_downloads_folder() / filename_shipments("xlsx"))
        path_str, _ = QFileDialog.getSaveFileName(
            self, "Guardar exportación", default_path, "Excel (*.xlsx)"
        )
        if not path_str:
            return

        path = Path(path_str)
        try:
            if export_shipments_excel(self._shipments, path):
                QMessageBox.information(
                    self,
                    "Exportación completada",
                    f"Se exportaron {len(self._shipments)} registros a:\n{path}",
                )
            else:
                QMessageBox.critical(self, "Error", "No se pudo exportar el archivo.")
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"No se pudo exportar: {exc}")
