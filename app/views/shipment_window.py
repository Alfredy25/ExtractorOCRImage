"""Ventana de captura y envío Paquetexpress."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDoubleSpinBox, QFrame, QGridLayout, QHBoxLayout,QLabel,
    QLineEdit, QMessageBox, QScrollArea, QSizePolicy, QSpinBox, QTextEdit, QVBoxLayout, QWidget,
)

from app.components.theme import SPACE
from app.components.widgets import (
    Banner, Card, divider, icon_label,
    labeled_field, section_label, subtitle, text_button,
)
from app.models.shipping import CoverageItem, ShippingDto
from app.services.paquetexpress_service import (
    PaquetexpressCoverageNotFoundError,
    PaquetexpressServiceError,PaquetexpressSessionExpiredError,
    PaquetexpressValidationError, build_shipment_draft, create_shipment,
    get_coverages_for_postal_code, normalize_shipment_fields, update_shipment,
)
from app.views.session_relogin import prompt_relogin_after_session_expired

# Campos con datos técnicos: se muestran en monoespaciada para facilitar el
# cotejo carácter a carácter contra la etiqueta del sobre.
_MONO_KEYS = {"rfc", "phone", "num_street", "package_code", "quantity", "weight", "length", "width", "height",}


def _coverage_from_shipment(shipment: ShippingDto) -> CoverageItem:
    """Arma un ítem de cobertura a partir del envío ya persistido."""
    return CoverageItem(
        postal_code=shipment.postal_code,
        colony=shipment.colony,
        municipality=shipment.city,
        city=shipment.city,
        state=shipment.state,
        coverage_type=shipment.coverage_type or "",
    )


class ShipmentWindow(QDialog):
    """Formulario de envío basado en cobertura + datos OCR."""

    def __init__(self, coverages: list[CoverageItem], ocr_form_data: dict[str, Any], 
                    parent=None, existing: ShippingDto | None = None):
        super().__init__(parent)
        self.setObjectName("ShipmentWindow")
        self._existing = existing
        self._updated_shipment: ShippingDto | None = None
        self.setWindowTitle(
            "Editar envío Paquetexpress" if existing is not None else "Crear envío Paquetexpress"
        )
        self.resize(1360, 860)
        self.setMinimumSize(1180, 720)
        self.setWindowFlag(Qt.WindowType.WindowMinMaxButtonsHint, True)
        self.setSizeGripEnabled(True)
        self._coverages = coverages
        self._ocr_form_data = ocr_form_data
        self._shipment_fields: dict[str, QWidget] = {}
        self._coverage_fields: dict[str, QLineEdit] = {}
        self._ocr_reference_fields: dict[str, QLineEdit] = {}
        self._draft_initialized = existing is not None
        self._coverage_refreshed = False
        self._setup_ui()
        self._load_coverages()
        if existing is None:
            self._load_ocr_reference()
        else:
            self._fill_from_existing()
        self.setWindowState(self.windowState() | Qt.WindowState.WindowMaximized)

    @classmethod
    def for_edit(cls, shipment: ShippingDto, parent=None) -> ShipmentWindow:
        """Diálogo de edición precargado con un envío existente."""
        return cls(
            coverages=[_coverage_from_shipment(shipment)],
            ocr_form_data={},
            parent=parent,
            existing=shipment,
        )

    @property
    def updated_shipment(self) -> ShippingDto | None:
        return self._updated_shipment

    @property
    def _is_edit(self) -> bool:
        return self._existing is not None

    # --- Construcción --------------------------------------------------

    def _setup_ui(self):
        """Arma el layout raíz y decide si hay columna OCR."""
        root = QVBoxLayout(self)
        root.setContentsMargins(SPACE["lg"], SPACE["md"], SPACE["lg"], SPACE["md"])
        root.setSpacing(SPACE["md"])

        root.addWidget(self._build_header())
        root.addWidget(divider())

        columns = QHBoxLayout()
        columns.setSpacing(SPACE["md"])
        if not self._is_edit:
            columns.addWidget(self._build_ocr_reference_card(), 4)

        right_column = QVBoxLayout()
        right_column.setSpacing(SPACE["md"])
        right_column.addWidget(self._build_coverage_banner())
        right_column.addWidget(self._build_coverage_card())
        right_column.addWidget(self._build_shipping_card(), 1)

        right_container = QWidget()
        right_container.setLayout(right_column)
        columns.addWidget(right_container, 8 if not self._is_edit else 1)

        columns_container = QWidget()
        columns_container.setLayout(columns)

        body_scroll = QScrollArea()
        body_scroll.setWidgetResizable(True)
        body_scroll.setFrameShape(QFrame.Shape.NoFrame)
        body_scroll.setWidget(columns_container)
        root.addWidget(body_scroll, 1)

    def _build_header(self) -> QWidget:
        """Título, subtítulo y botones de la cabecera."""
        header = QWidget()
        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACE["md"])

        title_column = QVBoxLayout()
        title_column.setSpacing(2)
        title = QLabel(
            "Editar envío Paquetexpress" if self._is_edit else "Crear envío Paquetexpress"
        )
        title.setProperty("role", "headline")
        title_column.addWidget(title)
        title_column.addWidget(
            subtitle(
                "Actualiza los datos del envío y consulta cobertura si cambia la colonia."
                if self._is_edit
                else "Valida la cobertura y completa los datos del envío."
            )
        )
        layout.addLayout(title_column)
        layout.addStretch(1)

        if not self._is_edit:
            btn_normalize = text_button("Normalizar campos", variant="ghost", icon="refresh")
            btn_normalize.setObjectName("shipmentNormalizeButton")
            btn_normalize.setMinimumHeight(38)
            btn_normalize.clicked.connect(self._on_normalize)
            layout.addWidget(btn_normalize)

        btn_cancel = text_button("Cancelar", variant="ghost", icon="close")
        btn_cancel.setObjectName("shipmentCancelButton")
        btn_cancel.setMinimumHeight(38)
        btn_cancel.clicked.connect(self.reject)
        layout.addWidget(btn_cancel)

        if self._is_edit:
            btn_submit = text_button("Guardar", variant="primary", icon="save")
            btn_submit.setObjectName("shipmentSaveButton")
        else:
            btn_submit = text_button("Crear envío", variant="primary", icon="send")
            btn_submit.setObjectName("shipmentCreateButton")
        btn_submit.setMinimumHeight(38)
        btn_submit.clicked.connect(self._on_submit)
        layout.addWidget(btn_submit)
        return header

    def _build_coverage_banner(self) -> Banner:
        """Banner verde de estado de cobertura."""
        self._banner = Banner(
            "check_circle",
            "Cobertura del registro" if self._is_edit else "Cobertura confirmada",
            self._coverage_banner_message(),
            tone="success",
        )
        return self._banner

    def _coverage_banner_message(self) -> str:
        """Texto del banner (en edición, hasta consultar cobertura, avisa que hay que refrescar)."""
        count = len(self._coverages)
        colonias = "colonia disponible" if count == 1 else "colonias disponibles"
        postal_code = self._coverages[0].postal_code if self._coverages else ""
        if self._is_edit and not self._coverage_refreshed:
            return (
                f"Código postal {postal_code}. Consulte cobertura para actualizar "
                f"colonia, estado, ciudad y tipo."
            )
        return (
            f"El código postal {postal_code} tiene cobertura Paquetexpress · "
            f"{count} {colonias}."
        )

    def _build_coverage_card(self) -> Card:
        """Combo de colonia + campos de solo lectura (+ botón consultar en edición)."""
        card = Card("Cobertura Paquetexpress", "map")

        self._colony_combo = QComboBox()
        self._colony_combo.currentIndexChanged.connect(self._on_colony_changed)
        card.body.addWidget(labeled_field("Colonia", self._colony_combo))

        if self._is_edit:
            btn_consult = text_button(
                "Consultar cobertura", variant="ghost", icon="search"
            )
            btn_consult.setObjectName("shipmentConsultCoverageButton")
            btn_consult.setMinimumHeight(38)
            btn_consult.clicked.connect(self._on_consult_coverage)
            card.body.addWidget(btn_consult)

        grid = QGridLayout()
        grid.setHorizontalSpacing(SPACE["md"])
        grid.setVerticalSpacing(SPACE["sm"])
        for column, (key, label) in enumerate(
            (
                ("postal_code", "Código Postal"),
                ("city", "Ciudad"),
                ("state", "Estado"),
                ("coverage_type", "Tipo de cobertura"),
            )
        ):
            self._coverage_fields[key] = self._readonly_line()
            grid.addWidget(
                labeled_field(label, self._coverage_fields[key], mono=key == "postal_code"),
                column // 2,
                column % 2,
            )
        card.body.addLayout(grid)
        return card

    def _build_shipping_card(self) -> Card:
        """Formulario Destinatario / Dirección / Paquete."""
        card = Card("Datos del envío", "edit_document")

        card.body.addWidget(
            self._section(
                "Destinatario",
                "person",
                [
                    [("Destinatario", "name_receiver", True, "text")],
                    [("RFC", "rfc", True, "text"), ("País", "country", False, "text")],
                ],
            )
        )
        card.body.addWidget(
            self._section(
                "Dirección",
                "place",
                [
                    [
                        ("Calle", "street", True, "text"),
                        ("Número exterior", "num_street", True, "text"),
                    ],
                    [
                        ("Teléfono", "phone", True, "text"),
                        ("Email", "email", True, "text"),
                    ],
                    [("Referencia de domicilio", "address_reference", True, "text")],
                ],
            )
        )
        # Comentarios y contenido van en filas propias (ancho completo), uno
        # debajo del otro: el texto largo no cabe bien en una sola línea.
        card.body.addWidget(
            self._section(
                "Paquete",
                "inventory_2",
                [
                    [
                        ("Código de paquete", "package_code", True, "int"),
                        ("Cantidad", "quantity", True, "int"),
                    ],
                    [("Comentarios", "comments", True, "textarea")],
                    [("Contenido", "content", True, "text")],
                    [
                        ("Peso (kg)", "weight", True, "double"),
                        ("Largo (cm)", "length", True, "double"),
                        ("Ancho (cm)", "width", True, "double"),
                        ("Alto (cm)", "height", True, "double"),
                    ],
                ],
            )
        )
        card.body.addStretch(1)
        return card

    def _build_ocr_reference_card(self) -> Card:
        """Columna OCR (solo lectura)."""
        card = Card("Datos OCR de referencia", "document_scanner")
        card.body.addWidget(
            subtitle(
                "Solo lectura: sirven para comparar con la cobertura y elegir "
                "la colonia correcta. No se envían al backend."
            )
        )
        card.body.addWidget(divider(soft=True))
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
            card.body.addWidget(
                labeled_field(label, line, mono=key in ("codigo_postal", "contacto"))
            )
        card.body.addStretch(1)
        return card

    """Fábrica de filas y widgets (QLineEdit, QSpinBox, QDoubleSpinBox, QTextEdit)."""
    def _section(self, title: str, icon: str, rows: list[list[tuple[str, str, bool, str]]]) -> QFrame:
        """Bloque de campos agrupados. Cada fila reparte su ancho a partes iguales."""
        box = QFrame()
        box.setObjectName("SectionBox")
        box.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        layout = QVBoxLayout(box)
        layout.setContentsMargins(SPACE["sm"] + 4, SPACE["sm"] + 2, SPACE["sm"] + 4, SPACE["sm"] + 4)
        layout.setSpacing(SPACE["sm"] + 2)

        header = QHBoxLayout()
        header.setSpacing(SPACE["xs"] + 2)
        header.addWidget(icon_label(icon, 15))
        header.addWidget(section_label(title))
        header.addStretch(1)
        layout.addLayout(header)

        for row in rows:
            if len(row) == 1:
                label, key, editable, widget_type = row[0]
                layout.addWidget(self._field(label, key, editable, widget_type))
                continue
            row_layout = QHBoxLayout()
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(SPACE["sm"] + 2)
            for label, key, editable, widget_type in row:
                row_layout.addWidget(self._field(label, key, editable, widget_type), 1)
            layout.addLayout(row_layout)
        return box

    def _field(self, label: str, key: str, editable: bool, widget_type: str) -> QWidget:
        if widget_type == "int":
            field_widget: QWidget = QSpinBox()
            field_widget.setRange(1, 999999)
            field_widget.setSingleStep(1)
            field_widget.setEnabled(editable)
            field_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        elif widget_type == "double":
            field_widget = QDoubleSpinBox()
            field_widget.setRange(0.00, 999999.99)
            field_widget.setDecimals(2)
            field_widget.setSingleStep(0.01)
            field_widget.setEnabled(editable)
            field_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        elif widget_type == "textarea":
            field_widget = QTextEdit()
            field_widget.setAcceptRichText(False)
            field_widget.setTabChangesFocus(True)
            field_widget.setMinimumHeight(72)
            field_widget.setMaximumHeight(110)
            field_widget.setReadOnly(not editable)
            field_widget.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
            )
            field_widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            field_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            field_widget.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        else:
            field_widget = QLineEdit()
            field_widget.setReadOnly(not editable)
            field_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._shipment_fields[key] = field_widget
        return labeled_field(label, field_widget, mono=key in _MONO_KEYS)

    # --- Valores de los campos -----------------------------------------

    @staticmethod
    def _set_field_value(widget: QWidget, value: Any):
        """Escribe texto o número en el widget correcto."""
        if isinstance(widget, QLineEdit):
            widget.setText(str(value or ""))
            return
        if isinstance(widget, QTextEdit):
            widget.setPlainText(str(value or ""))
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
        """Lee el valor (strip en textos, redondeo a 2 decimales en doubles)."""
        if isinstance(widget, QLineEdit):
            return widget.text().strip()
        if isinstance(widget, QTextEdit):
            return widget.toPlainText().strip()
        if isinstance(widget, QSpinBox):
            return widget.value()
        if isinstance(widget, QDoubleSpinBox):
            return round(widget.value(), 2)
        return ""

    @staticmethod
    def _readonly_line() -> QLineEdit:
        """QLineEdit de solo lectura, sin foco."""
        line = QLineEdit()
        line.setReadOnly(True)
        line.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        return line

    # --- Carga de datos ------------------------------------------------

    def _load_coverages(self):
        """Llena el combo con CoverageItem y aplica la primera."""
        self._colony_combo.blockSignals(True)
        self._colony_combo.clear()
        for item in self._coverages:
            self._colony_combo.addItem(item.colony, item)
        self._colony_combo.blockSignals(False)
        if self._colony_combo.count() > 0:
            self._colony_combo.setCurrentIndex(0)
            self._apply_selected_coverage()

    def _load_ocr_reference(self):
        """Rellena la columna OCR (crear)."""
        campos = self._ocr_form_data.get("campos") or {}
        for key, widget in self._ocr_reference_fields.items():
            widget.setText(str(campos.get(key) or "").strip())

    def _fill_from_existing(self):
        """Rellena el formulario desde ShippingDto (editar)."""
        shipment = self._existing
        if shipment is None:
            return
        values = {
            "name_receiver": shipment.name_receiver,
            "rfc": shipment.rfc,
            "country": shipment.country,
            "street": shipment.street,
            "num_street": shipment.num_street,
            "email": str(shipment.email) if shipment.email else "",
            "phone": shipment.phone,
            "address_reference": shipment.address_reference,
            "quantity": shipment.quantity,
            "package_code": shipment.package_code,
            "comments": shipment.comments,
            "content": shipment.content,
            "weight": shipment.weight,
            "length": shipment.length,
            "width": shipment.width,
            "height": shipment.height,
        }
        for key, value in values.items():
            widget = self._shipment_fields.get(key)
            if widget is not None:
                self._set_field_value(widget, value)

    def _on_consult_coverage(self):
        if self._existing is None:
            return
        postal_code = self._existing.postal_code
        try:
            coverages = get_coverages_for_postal_code(postal_code)
        except PaquetexpressCoverageNotFoundError as exc:
            QMessageBox.warning(self, "Sin cobertura", str(exc))
            return
        except PaquetexpressSessionExpiredError as exc:
            prompt_relogin_after_session_expired(
                self, f"No se pudo consultar cobertura: {exc}"
            )
            return
        except PaquetexpressServiceError as exc:
            QMessageBox.critical(
                self, "Error", f"No se pudo consultar cobertura: {exc}"
            )
            return

        previous_colony = self._existing.colony
        self._coverages = coverages
        self._coverage_refreshed = True
        self._load_coverages()
        for index in range(self._colony_combo.count()):
            item = self._colony_combo.itemData(index)
            if isinstance(item, CoverageItem) and item.colony == previous_colony:
                self._colony_combo.setCurrentIndex(index)
                break
        self._banner.set_title("Cobertura confirmada")
        self._banner.set_message(self._coverage_banner_message())

    def _on_colony_changed(self, _index: int):
        self._apply_selected_coverage()

    def _selected_coverage(self) -> CoverageItem | None:
        data = self._colony_combo.currentData()
        return data if isinstance(data, CoverageItem) else None

    def _apply_selected_coverage(self):
        """Copia cobertura a los campos de solo lectura; la primera vez en crear, arma el borrador OCR → formulario."""
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

    # --- Envío ---------------------------------------------------------

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
        action = "actualizar" if self._is_edit else "crear"
        try:
            if self._existing is not None:
                self._updated_shipment = update_shipment(
                    self._existing.id_shipping, payload
                )
            else:
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
            prompt_relogin_after_session_expired(
                self, f"No se pudo {action} el envío: {exc}"
            )
            return
        except PaquetexpressServiceError as exc:
            QMessageBox.critical(
                self, "Error", f"No se pudo {action} el envío: {exc}"
            )
            return

        if self._is_edit:
            QMessageBox.information(self, "Éxito", "Envío actualizado correctamente.")
        else:
            QMessageBox.information(self, "Éxito", "Envío creado correctamente.")
        self.accept()

    def _on_normalize(self):
        payload: dict[str, Any] = {key: self._get_field_value(widget) for key, widget in self._shipment_fields.items()}
        campos_normalizados = normalize_shipment_fields(payload)
        for key, widget in self._shipment_fields.items():
            keys = campos_normalizados.keys()
            if key in keys:
                self._set_field_value(widget, campos_normalizados.get(key, ""))