"""Ventana de captura y envío Paquetexpress."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.models.shipping import CoverageItem
from app.services.paquetexpress_service import (PaquetexpressServiceError, PaquetexpressSessionExpiredError,
                                                    PaquetexpressValidationError, build_shipment_draft, 
                                                    create_shipment)
from app.views.session_relogin import prompt_relogin_after_session_expired


class ShipmentWindow(QDialog):
    """Formulario de envío basado en cobertura + datos OCR."""

    _INLINE_LABEL_WIDTH = 108

    def __init__(self, coverages: list[CoverageItem], ocr_form_data: dict[str, Any], parent=None):
        super().__init__(parent)
        self.setObjectName("ShipmentWindow")
        self.setWindowTitle("Crear envío Paquetexpress")
        self.resize(1360, 860)
        self.setMinimumSize(1180, 720)
        self.setWindowFlag(Qt.WindowType.WindowMinMaxButtonsHint, True)
        self.setSizeGripEnabled(True)
        self._coverages = coverages
        self._ocr_form_data = ocr_form_data
        self._shipment_fields: dict[str, QWidget] = {}
        self._coverage_fields: dict[str, QLineEdit] = {}
        self._ocr_reference_fields: dict[str, QLineEdit] = {}
        self._draft_initialized = False
        self._setup_ui()
        self._load_coverages()
        self._load_ocr_reference()
        self.setWindowState(self.windowState() | Qt.WindowState.WindowMaximized)

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        columns_container = QWidget()
        columns_layout = QGridLayout()
        columns_container.setLayout(columns_layout)
        columns_layout.setContentsMargins(0, 0, 0, 0)
        columns_layout.setHorizontalSpacing(12)
        columns_layout.addWidget(self._build_ocr_reference_group(), 0, 0)
        columns_layout.addWidget(self._build_coverage_group(), 0, 1)
        columns_layout.addWidget(self._build_shipping_group(), 0, 2)
        columns_layout.setColumnStretch(0, 1)
        columns_layout.setColumnStretch(1, 1)
        columns_layout.setColumnStretch(2, 2)

        body_scroll = QScrollArea()
        body_scroll.setWidgetResizable(True)
        body_scroll.setFrameShape(QFrame.Shape.NoFrame)
        body_scroll.setWidget(columns_container)
        root.addWidget(body_scroll, 1)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        actions.addStretch()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setObjectName("shipmentCancelButton")
        btn_cancel.clicked.connect(self.reject)
        btn_submit = QPushButton("Crear envío")
        btn_submit.setObjectName("shipmentCreateButton")
        btn_submit.clicked.connect(self._on_submit)
        actions.addWidget(btn_cancel)
        actions.addWidget(btn_submit)
        root.addLayout(actions)
        root.setStretch(0, 1)

    def _build_coverage_group(self) -> QGroupBox:
        group = QGroupBox("Cobertura Paquetexpress")
        group.setMinimumWidth(290)
        form = QFormLayout(group)

        self._coverage_fields["postal_code"] = self._readonly_line()
        form.addRow("Código Postal:", self._coverage_fields["postal_code"])

        self._colony_combo = QComboBox()
        self._colony_combo.currentIndexChanged.connect(self._on_colony_changed)
        form.addRow("Colonia:", self._colony_combo)

        self._coverage_fields["city"] = self._readonly_line()
        form.addRow("Ciudad:", self._coverage_fields["city"])

        self._coverage_fields["state"] = self._readonly_line()
        form.addRow("Estado:", self._coverage_fields["state"])

        self._coverage_fields["coverage_type"] = self._readonly_line()
        form.addRow("Tipo Cobertura:", self._coverage_fields["coverage_type"])
        return group

    def _build_shipping_group(self) -> QGroupBox:
        group = QGroupBox("Datos del Envío")
        wrapper = QVBoxLayout(group)
        wrapper.setSpacing(4)

        form_grid = QGridLayout()
        form_grid.setHorizontalSpacing(10)
        form_grid.setVerticalSpacing(4)

        row = 0
        form_grid.addWidget(
            self._labeled_field("Destinatario", "name_receiver", True, inline=True),
            row,
            0,
            1,
            2,
        )
        row += 1
        form_grid.addWidget(self._labeled_field("RFC", "rfc", True), row, 0)
        form_grid.addWidget(self._labeled_field("País", "country", False), row, 1)
        row += 1
        form_grid.addWidget(self._labeled_field("Calle", "street", True), row, 0)
        form_grid.addWidget(self._labeled_field("Número Exterior", "num_street", True), row, 1)
        row += 1
        form_grid.addWidget(self._labeled_field("Teléfono", "phone", True), row, 0)
        form_grid.addWidget(self._labeled_field("Email", "email", True), row, 1)
        row += 1
        form_grid.addWidget(self._labeled_field("Referencia de Domicilio", "address_reference", True), row, 0, 1, 2)
        row += 1
        
        form_grid.addWidget(
            self._labeled_field("Código de Paquete", "package_code", True,
                widget_type="int",
                inline=True,),row,0)
        form_grid.addWidget(
            self._labeled_field("Cantidad", "quantity", True, widget_type="int",
                inline=True,),row,1)
        row += 1
        form_grid.addWidget(
            self._labeled_field("Contenido", "content", True, inline=True),
            row,
            0,
            1,
            2,
        )
        row += 1

        size_box = QGroupBox("Dimensiones")
        size_grid = QGridLayout(size_box)
        size_grid.setHorizontalSpacing(8)
        size_grid.setVerticalSpacing(6)
        size_grid.addWidget(
            self._labeled_field("Peso (kg)", "weight", True, widget_type="double"),
            0,
            0,
        )
        size_grid.addWidget(
            self._labeled_field("Largo (cm)", "length", True, widget_type="double"),
            0,
            1,
        )
        size_grid.addWidget(
            self._labeled_field("Ancho (cm)", "width", True, widget_type="double"),
            0,
            2,
        )
        size_grid.addWidget(
            self._labeled_field("Alto (cm)", "height", True, widget_type="double"),
            0,
            3,
        )
        form_grid.addWidget(size_box, row, 0, 1, 2)

        wrapper.addLayout(form_grid)
        return group

    def _build_ocr_reference_group(self) -> QGroupBox:
        group = QGroupBox("Datos OCR de Referencia")
        group.setMinimumWidth(300)
        form = QFormLayout(group)
        for key, label in (
            ("nombre_titulo", "Nombre OCR"),
            ("cargo_dependencia", "Cargo OCR"),
            ("estado", "Estado OCR"),
            ("municipio_alcaldia", "Ciudad OCR"),
            ("colonia", "Colonia OCR"),
            ("codigo_postal", "Código Postal OCR"),
            ("direccion", "Dirección OCR"),
            ("contacto", "Contacto OCR"),
            ("indicaciones", "Indicaciones OCR"),
        ):
            line = self._readonly_line()
            self._ocr_reference_fields[key] = line
            form.addRow(f"{label}:", line)
        return group

    @staticmethod
    def _add_section_title(parent_layout: QVBoxLayout, text: str):
        title = QLabel(text)
        title.setStyleSheet("font-weight: 700;")
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        parent_layout.addWidget(title)
        parent_layout.addWidget(line)

    def _labeled_field(
        self,
        label: str,
        key: str,
        editable: bool,
        widget_type: str = "text",
        inline: bool = False,
    ) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container) if inline else QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)
        lbl = QLabel(label)
        if inline:
            container.setProperty("shipmentInlineRow", True)
            lbl.setProperty("shipmentInlineLabel", True)
            lbl.setMinimumWidth(self._INLINE_LABEL_WIDTH)
            lbl.setMaximumWidth(self._INLINE_LABEL_WIDTH)
            lbl.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        if widget_type == "int":
            field_widget = QSpinBox()
            field_widget.setRange(1, 999999)
            field_widget.setSingleStep(1)
            field_widget.setEnabled(editable)
        elif widget_type == "double":
            field_widget = QDoubleSpinBox()
            field_widget.setRange(0.00, 999999.99)
            field_widget.setDecimals(2)
            field_widget.setSingleStep(0.01)
            field_widget.setEnabled(editable)
        else:
            field_widget = QLineEdit()
            field_widget.setReadOnly(not editable)
        field_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._shipment_fields[key] = field_widget
        layout.addWidget(lbl)
        layout.addWidget(field_widget)
        if inline:
            layout.setSpacing(4)
            layout.setStretch(1, 1)
        return container

    @staticmethod
    def _set_field_value(widget: QWidget, value: Any):
        if isinstance(widget, QLineEdit):
            widget.setText(str(value or ""))
            return
        if isinstance(widget, QSpinBox):
            try:
                int_value = int(value)
            except (TypeError, ValueError):
                int_value = widget.minimum()
            widget.setValue(max(widget.minimum(), int_value))
            return
        if isinstance(widget, QDoubleSpinBox):
            try:
                double_value = float(value)
            except (TypeError, ValueError):
                double_value = widget.minimum()
            widget.setValue(max(widget.minimum(), double_value))
            return

    @staticmethod
    def _get_field_value(widget: QWidget) -> Any:
        if isinstance(widget, QLineEdit):
            return widget.text().strip()
        if isinstance(widget, QSpinBox):
            return widget.value()
        if isinstance(widget, QDoubleSpinBox):
            return round(widget.value(), 2)
        return ""

    @staticmethod
    def _readonly_line() -> QLineEdit:
        line = QLineEdit()
        line.setReadOnly(True)
        line.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        return line

    def _load_coverages(self):
        self._colony_combo.blockSignals(True)
        self._colony_combo.clear()
        for item in self._coverages:
            self._colony_combo.addItem(item.colony, item)
        self._colony_combo.blockSignals(False)
        if self._colony_combo.count() > 0:
            self._colony_combo.setCurrentIndex(0)
            self._apply_selected_coverage()

    def _load_ocr_reference(self):
        campos = self._ocr_form_data.get("campos") or {}
        for key, widget in self._ocr_reference_fields.items():
            widget.setText(str(campos.get(key) or "").strip())

    def _on_colony_changed(self, _index: int):
        self._apply_selected_coverage()

    def _selected_coverage(self) -> CoverageItem | None:
        data = self._colony_combo.currentData()
        return data if isinstance(data, CoverageItem) else None

    def _apply_selected_coverage(self):
        selected = self._selected_coverage()
        if selected is None:
            return
        self._coverage_fields["postal_code"].setText(selected.postal_code)
        self._coverage_fields["city"].setText(selected.city)
        self._coverage_fields["state"].setText(selected.state)
        self._coverage_fields["coverage_type"].setText(selected.coverage_type)
        if not self._draft_initialized:
            draft = build_shipment_draft(self._ocr_form_data, selected)
            for key, widget in self._shipment_fields.items():
                self._set_field_value(widget, draft.get(key, ""))
            self._draft_initialized = True

    def _shipment_payload_from_form(self) -> dict[str, Any]:
        selected = self._selected_coverage()
        if selected is None:
            return {}
        payload: dict[str, Any] = {
            key: self._get_field_value(widget)
            for key, widget in self._shipment_fields.items()
        }
        # Estos campos SIEMPRE salen de cobertura seleccionada.
        payload["state"] = selected.state
        payload["city"] = selected.city
        payload["colony"] = selected.colony
        payload["postal_code"] = selected.postal_code
        payload["coverage_type"] = selected.coverage_type
        return payload

    def _on_submit(self):
        payload = self._shipment_payload_from_form()
        if not payload:
            QMessageBox.critical(self, "Error", "No hay cobertura seleccionada.")
            return
        try:
            create_shipment(payload)
        except PaquetexpressValidationError as exc:
            details = "\n\n".join(
                f"• {error['campo']} {error['error']}." for error in exc.errors
            )
            QMessageBox.critical(
                self,
                "Errores de validación",
                f"Se encontraron los siguientes errores:\n\n{details}",
            )
            return
        except PaquetexpressSessionExpiredError as exc:
            prompt_relogin_after_session_expired(self, f"No se pudo crear el envío: {exc}")
            return
        except PaquetexpressServiceError as exc:
            QMessageBox.critical(self, "Error", f"No se pudo crear el envío: {exc}")
            return

        QMessageBox.information(self, "Éxito", "Envío creado correctamente.")
        self.accept()
