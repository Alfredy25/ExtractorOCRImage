"""Diálogo de exportación: rango de fecha y hora por separado, sede opcional, Descargas por defecto."""
from app.models.shipping import ShippingDto
from datetime import datetime, time
from pathlib import Path

from PySide6.QtCore import QDate, QStandardPaths, QTime
from PySide6.QtWidgets import (QDateEdit, QDialog, QFileDialog, QHBoxLayout,
                                QMessageBox, QTableWidget, QTimeEdit, QVBoxLayout)

from app.components.theme import SPACE
from app.components.widgets import (text_button, field_label, card_title)
from app.services.export_service import filename_shipments, export_shipments_excel
from app.views.session_relogin import prompt_relogin_after_session_expired
from app.services.paquetexpress_service import PaquetexpressSessionExpiredError, PaquetexpressServiceError, list_shipments_by_date_range
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem

def _downloads_folder() -> Path:
    """Carpeta Descargas del usuario (nombre localizado vía Qt)."""
    loc = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.DownloadLocation
    )
    if loc:
        return Path(loc)
    return Path.home() / "Downloads"



class ExportShipments(QDialog):
    """Exportar registros obtenidos de la API a Excel/CSV."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Exportar envíos")
        self.setMinimumSize(1024, 900)
        self._setup_ui()
        

    def _setup_ui(self):
        layout_main = QVBoxLayout()
        layout_main.setContentsMargins(SPACE["lg"], SPACE["lg"], SPACE["lg"], SPACE["lg"])
        layout_main.setSpacing(SPACE["md"])
        self.setLayout(layout_main)
        title = card_title("Exportar envíos")
        layout_main.addWidget(title)
        layout_header = QHBoxLayout()

        label_fecha_inicio = field_label("Desde")
        self._date_from = QDateEdit()
        self._date_from.setCalendarPopup(True)
        self._date_from.setDisplayFormat("dd/MM/yyyy")
        self._date_from.setDate(QDate.currentDate().addDays(-1))
        label_hora_inicio = field_label("Desde")
        self._time_from = QTimeEdit()
        self._time_from.setDisplayFormat("HH:mm")
        self._time_from.setTime(QTime(8, 00))
        
        label_fecha_fin = field_label("Hasta")
        self._date_to = QDateEdit()
        self._date_to.setCalendarPopup(True)
        self._date_to.setDisplayFormat("dd/MM/yyyy")
        self._date_to.setDate(QDate.currentDate())
        label_hora_fin = field_label("Hasta")
        self._time_to = QTimeEdit()
        self._time_to.setDisplayFormat("HH:mm")
        date_today = datetime.now()
        self._time_to.setTime(QTime(date_today.hour, date_today.minute))
        btn_consult = text_button("Consultar", variant="primary", icon="edit_document")
        btn_consult.setMinimumHeight(38)
        btn_consult.clicked.connect(self._do_consult)

        layout_header.addWidget(label_fecha_inicio)
        layout_header.addWidget(self._date_from)
        layout_header.addWidget(label_hora_inicio)
        layout_header.addWidget(self._time_from)
        layout_header.addWidget(label_fecha_fin)
        layout_header.addWidget(self._date_to)
        layout_header.addWidget(label_hora_fin)
        layout_header.addWidget(self._time_to)
        layout_header.addWidget(btn_consult)
        layout_main.addLayout(layout_header)

        # Configuración de la tabla
        self.columns = ["ID envío", "Folio", "Destinatario", "RFC", "País", "Estado", "Ciudad", "Colonia", "Calle",
                        "Número", "Código postal", "Correo electrónico", "Teléfono", "Referencia", "Cantidad", 
                        "Código de paquete", "Contenido", "Peso", "Largo", "Ancho", "Alto", "Tipo de cobertura", "Comentarios", "Fecha de creación"]
        self.tabla = QTableWidget(self)
        self.tabla.setObjectName("ShipmentsTable")
        self.tabla.setColumnCount(len(self.columns))
        self.tabla.setHorizontalHeaderLabels(self.columns)

        layout_main.addWidget(self.tabla)

        layout_main.addLayout(self._build_actions())

    @staticmethod
    def _qtime_to_pytime(qt: QTime) -> time:
        return time(qt.hour(), qt.minute(), qt.second())
    

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

    def _do_consult(self):
        d0 = self._date_from.date().toPython()
        t0 = self._qtime_to_pytime(self._time_from.time())
        d1 = self._date_to.date().toPython()
        t1 = self._qtime_to_pytime(self._time_to.time())

        dt_desde = datetime.combine(d0, t0)
        print(dt_desde)
        dt_hasta = datetime.combine(d1, t1)
        print(dt_hasta)
        if dt_desde > dt_hasta:
            QMessageBox.warning(self, "Rango inválido", "La fecha y hora 'Desde' deben ser anteriores o iguales a 'Hasta'.")
            return
        try:
            shipments = list_shipments_by_date_range(dt_desde, dt_hasta)
        except PaquetexpressSessionExpiredError as e:
            prompt_relogin_after_session_expired(self, f"No se pudieron obtener envíos: {e}")
            return
        except PaquetexpressServiceError as e:
            QMessageBox.critical(self, "Error", f"No se pudieron obtener envíos: {e}")
            return
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error inesperado al obtener envíos: {e}")
            return
        if not shipments:
            QMessageBox.critical(self, "Sin datos", "No hay envíos en el rango:")
            return
        self.fill_table(shipments)
        self._shipments = shipments
    
    def fill_table(self, shipments: list[ShippingDto]) -> None:
        self.tabla.clearContents()
        self.tabla.setRowCount(len(shipments))

        for row, shipment in enumerate(shipments):
            values = [shipment.id_shipping, shipment.id_folio, shipment.name_receiver, shipment.rfc,
                shipment.country, shipment.state, shipment.city, shipment.colony, shipment.street, shipment.num_street,
                shipment.postal_code, str(shipment.email), shipment.phone, shipment.address_reference, str(shipment.quantity),
                str(shipment.package_code), shipment.content, str(shipment.weight), str(shipment.length), str(shipment.width), str(shipment.height),
                shipment.coverage_type, shipment.comments, shipment.created_at.isoformat() if shipment.created_at else None]

            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value) if value is not None else "")
                self.tabla.setItem(row, column, item)           

    def _do_export(self):
        ext = "xlsx"
        default_name = filename_shipments(ext)
        default_path = str(_downloads_folder() / default_name)

        path_str, _ = QFileDialog.getSaveFileName(self, "Guardar exportación", default_path, "Excel (*.xlsx)")
        if not path_str:
            return

        path = Path(path_str)
        if not getattr(self, "_shipments", None):
            QMessageBox.critical(self, "Sin datos", "Consulta primero un rango.")
            return
        try:
            if export_shipments_excel(self._shipments, path):
                QMessageBox.information(self,"Exportación completada",
                f"Se exportaron {len(self._shipments)} registros a:\n{path}")
                self.accept()
            else:
                QMessageBox.critical(self, "Error", f"No se pudo exportar ({type(e).__name__}: {e})")
                return
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo exportar: {e}")
            return

            
    
        
