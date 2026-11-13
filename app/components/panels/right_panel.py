"""Inspector del Workspace: búsqueda de destinatario y extracción OCR.

Las dos ramas del flujo de envío viven aquí, cada una en una sección plegable.
La de **Destinatario** se abre primero porque el flujo busca antes de extraer;
la de **Datos extraídos** solo hace falta cuando la búsqueda no encuentra nada.

Mantiene el contrato de datos anterior (``get_form_data`` / ``set_form_data``
con las claves de ``FIELD_KEYS``) y el selector de SEDE.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLineEdit,
    QProgressBar,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.components.autocomplete_combo import AutocompleteComboBox
from app.components.receiver_picker import ReceiverPicker
from app.components.theme import SPACE
from app.components.widgets import (
    Card,
    CollapsibleSection,
    chip,
    divider,
    icon_label,
    labeled_field,
    section_label,
    subtitle,
    text_button,
)
from app.config import SEDES
from app.models.field_schema import FIELD_KEYS
from app.services import catalogs_service

_VOLANTE_FIELDS = (("name", "Nombre del volante", "upper", 35),)

# Etiquetas legibles para las claves del esquema OCR.
FIELD_LABELS = {
    "nombre_titulo": "Nombre / Título",
    "cargo_dependencia": "Cargo / Dependencia",
    "direccion": "Dirección",
    "colonia": "Colonia",
    "municipio_alcaldia": "Municipio / Alcaldía",
    "estado": "Estado",
    "codigo_postal": "Código Postal",
    "numero_volante": "Número de volante",
    "extras": "Extras",
    "contacto": "Contacto",
    "indicaciones": "Indicaciones",
}

# Campos que contienen datos técnicos y se muestran en monoespaciada.
MONO_FIELDS = {"codigo_postal", "numero_volante", "contacto"}


class _NoWheelComboBox(QComboBox):
    """La rueda del ratón no cambia la sede; el Inspector puede seguir haciendo scroll."""

    def wheelEvent(self, event: QWheelEvent) -> None:
        event.ignore()

# Agrupación visual: (título, icono, filas). Cada fila es una lista de claves
# que se colocan una al lado de la otra.
SECTIONS: list[tuple[str, str, list[list[str]]]] = [
    ("Destinatario", "person", [["nombre_titulo"], ["cargo_dependencia"]]),
    (
        "Dirección",
        "place",
        [["direccion"], ["colonia"], ["municipio_alcaldia", "estado"], ["codigo_postal"]],
    ),
    ("Contacto y notas", "mail", [["contacto"], ["indicaciones"]]),
    ("Control interno", "numbers", [["numero_volante"], ["extras"]]),
]


class RightPanel(Card):
    """Tarjeta lateral con las dos ramas del flujo y las acciones del registro."""

    send_to_ai_clicked = Signal()
    check_coverage_clicked = Signal()
    save_clicked = Signal()
    sede_changed = Signal()
    form_changed = Signal()
    create_shipment_for_receiver_clicked = Signal()
    receiver_selected = Signal(object, object)
    receiver_cleared = Signal()
    edit_receiver_clicked = Signal(object)

    def __init__(self, parent: QWidget | None = None):
        super().__init__("Inspector", "dashboard", parent)
        self._fields: dict[str, QLineEdit] = {}
        self._receiver = None
        self._address = None
        self.set_body_margins(0, 0, 0, 0)
        self._setup_ui()

    # --- Construcción --------------------------------------------------

    def _setup_ui(self) -> None:
        self._status_chip = chip("SIN DATOS", tone="neutral")
        self.add_header_widget(self._status_chip)

        self.body.addWidget(self._build_scroll_area(), 1)
        self.body.addWidget(divider(soft=True))
        self.body.addWidget(self._build_footer())

    def _build_scroll_area(self) -> QScrollArea:
        content = QWidget()
        content.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(SPACE["md"], SPACE["md"], SPACE["md"], SPACE["md"])
        layout.setSpacing(SPACE["md"])

        self._receiver_section = self._build_receiver_section()
        layout.addWidget(self._receiver_section)
        self._extraction_section = self._build_extraction_section()
        layout.addWidget(self._extraction_section)
        layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(content)
        return scroll

    def _build_receiver_section(self) -> CollapsibleSection:
        """Paso 2 del flujo: buscar con lo que se lee en la foto, sin OCR."""
        section = CollapsibleSection("Destinatario", "person", expanded=True)
        section.body.addWidget(
            subtitle(
                "Busque al destinatario con lo que lee en la foto. Si aparece, "
                "elija un domicilio y cree el envío sin extraer."
            )
        )

        self._picker = ReceiverPicker()
        self._picker.receiver_selected.connect(self._on_receiver_selected)
        self._picker.selection_cleared.connect(self._on_receiver_cleared)
        self._picker.empty_results.connect(self._on_empty_results)
        self._picker.edit_requested.connect(self.edit_receiver_clicked.emit)
        section.body.addWidget(self._picker)

        self._btn_create_shipment = text_button(
            "Crear envío con este destinatario", variant="primary", icon="local_shipping"
        )
        self._btn_create_shipment.setObjectName("createShipmentButton")
        self._btn_create_shipment.setMinimumHeight(36)
        self._btn_create_shipment.setEnabled(False)
        self._btn_create_shipment.clicked.connect(
            self.create_shipment_for_receiver_clicked.emit
        )
        section.body.addWidget(self._btn_create_shipment)
        return section

    def _build_extraction_section(self) -> CollapsibleSection:
        """Rama 4b: solo se usa cuando la búsqueda no trae coincidencias."""
        section = CollapsibleSection("Datos extraídos", "data_object", expanded=False)
        section.body.addWidget(
            subtitle(
                "Solo si la búsqueda no encontró al destinatario: extraiga la "
                "foto, escriba a mano el número de volante y consulte cobertura "
                "con el código postal del OCR."
            )
        )
        section.body.addWidget(self._build_sede_section())

        placed: set[str] = set()
        for title, icon, rows in SECTIONS:
            keys = [key for row in rows for key in row if key in FIELD_KEYS]
            if not keys:
                continue
            placed.update(keys)
            section.body.addWidget(self._build_field_section(title, icon, rows))

        # Red de seguridad: si FIELD_KEYS crece, el campo nuevo sigue apareciendo.
        leftover = [key for key in FIELD_KEYS if key not in placed]
        if leftover:
            section.body.addWidget(
                self._build_field_section("Otros datos", "tune", [[key] for key in leftover])
            )

        section.body.addWidget(self._build_raw_section())
        section.body.addWidget(self._build_extraction_actions())
        return section

    def _build_extraction_actions(self) -> QWidget:
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACE["sm"])

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)  # Indeterminado: no conocemos la duración
        self._progress.setTextVisible(False)
        self._progress.hide()
        layout.addWidget(self._progress)

        self._btn_send = text_button("Enviar a IA", variant="primary", icon="auto_awesome")
        self._btn_send.setMinimumHeight(38)
        self._btn_send.clicked.connect(self.send_to_ai_clicked.emit)
        layout.addWidget(self._btn_send)

        self._btn_coverage = text_button(
            "Consultar cobertura", variant="ghost", icon="local_shipping"
        )
        self._btn_coverage.setMinimumHeight(34)
        self._btn_coverage.clicked.connect(self.check_coverage_clicked.emit)
        layout.addWidget(self._btn_coverage)
        return box

    def _build_sede_section(self) -> QFrame:
        box, layout = self._section_box("Ubicación", "apartment")
        self._sede_combo = _NoWheelComboBox()
        self._sede_combo.addItem("Seleccione una SEDE", None)
        for sede in SEDES:
            self._sede_combo.addItem(sede, sede)
        self._sede_combo.currentIndexChanged.connect(lambda _index: self.sede_changed.emit())
        layout.addWidget(labeled_field("SEDE", self._sede_combo))
        return box

    def _build_field_section(
        self, title: str, icon: str, rows: list[list[str]]
    ) -> QFrame:
        box, layout = self._section_box(title, icon)
        for row_keys in rows:
            keys = [key for key in row_keys if key in FIELD_KEYS]
            if not keys:
                continue
            if len(keys) == 1:
                layout.addWidget(self._build_field(keys[0]))
                continue
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(SPACE["sm"])
            for key in keys:
                row.addWidget(self._build_field(key), 1)
            layout.addLayout(row)
        return box

    def _build_field(self, key: str) -> QWidget:
        label = FIELD_LABELS.get(key, key.replace("_", " ").capitalize())
        if key == "numero_volante":
            return self._build_volante_field(label)
        line = QLineEdit()
        line.setPlaceholderText("—")
        line.textChanged.connect(lambda _text: self.form_changed.emit())
        self._fields[key] = line
        return labeled_field(label, line, mono=key in MONO_FIELDS)

    def _build_volante_field(self, label: str) -> QWidget:
        """Busca o crea el volante suelto. El texto escrito también se guarda."""
        combo = AutocompleteComboBox(
            catalogs_service.search_volantes,
            lambda item: item.name,
            create_fn=lambda data: catalogs_service.create_volante(data["name"]),
            create_title="Nuevo volante",
            create_fields=list(_VOLANTE_FIELDS),
            placeholder="Buscar o escribir volante",
        )
        combo.selection_changed.connect(self.form_changed.emit)
        combo._combo.lineEdit().textChanged.connect(lambda _text: self.form_changed.emit())
        self._fields["numero_volante"] = combo
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACE["xs"])
        layout.addWidget(labeled_field(label, combo, mono=True))
        layout.addWidget(combo.status_widget())
        return box

    def _build_raw_section(self) -> QFrame:
        box, layout = self._section_box("Texto OCR", "description")

        self._destinatario_raw = QTextEdit()
        self._destinatario_raw.setMaximumHeight(90)
        self._destinatario_raw.setProperty("role", "mono")
        self._destinatario_raw.textChanged.connect(self.form_changed.emit)
        layout.addWidget(labeled_field("Texto bruto (destinatario_raw)", self._destinatario_raw))

        self._observaciones = QTextEdit()
        self._observaciones.setMaximumHeight(80)
        self._observaciones.textChanged.connect(self.form_changed.emit)
        layout.addWidget(labeled_field("Observaciones IA", self._observaciones))
        return box

    @staticmethod
    def _section_box(title: str, icon: str) -> tuple[QFrame, QVBoxLayout]:
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
        return box, layout

    def _build_footer(self) -> QWidget:
        footer = QWidget()
        layout = QVBoxLayout(footer)
        layout.setContentsMargins(SPACE["md"], SPACE["sm"] + 4, SPACE["md"], SPACE["md"])
        layout.setSpacing(SPACE["sm"])

        self._btn_save = text_button("Guardar registro", variant="primary", icon="save")
        self._btn_save.setMinimumHeight(34)
        self._btn_save.clicked.connect(self.save_clicked.emit)
        layout.addWidget(self._btn_save)
        return footer

    # --- Destinatario --------------------------------------------------

    def _on_receiver_selected(self, receiver, address) -> None:
        self._receiver = receiver
        self._address = address
        self.receiver_selected.emit(receiver, address)

    def _on_receiver_cleared(self) -> None:
        self._receiver = None
        self._address = None
        self.receiver_cleared.emit()

    def _on_empty_results(self) -> None:
        """Cero coincidencias abre la extracción: es el paso 4b del flujo."""
        self._extraction_section.set_expanded(True)

    def selected_receiver(self):
        return self._receiver

    def selected_address(self):
        return self._address

    def selected_contact(self):
        return self._picker.selected_contact()

    def show_receiver(
        self,
        receiver,
        preferred_address_id: int | None = None,
        preferred_contact_id: int | None = None,
    ) -> None:
        """Refresca la ficha tras editar o agregar domicilio/contacto."""
        self._picker.show_receiver(receiver, preferred_address_id, preferred_contact_id)

    def reset_receiver(self) -> None:
        """Olvida la búsqueda anterior al cambiar de imagen."""
        self._picker.reset()
        self._receiver_section.set_expanded(True)
        self._extraction_section.set_expanded(False)

    # --- Estado --------------------------------------------------------

    def _set_status(self, text: str, tone: str) -> None:
        self._status_chip.setText(text)
        self._status_chip.setProperty("tone", tone)
        style = self._status_chip.style()
        style.unpolish(self._status_chip)
        style.polish(self._status_chip)

    def set_send_enabled(self, enabled: bool) -> None:
        self._btn_send.setEnabled(enabled)

    def set_create_shipment_enabled(self, enabled: bool) -> None:
        self._btn_create_shipment.setEnabled(enabled)

    def set_save_enabled(self, enabled: bool) -> None:
        self._btn_save.setEnabled(enabled)

    def set_coverage_enabled(self, enabled: bool) -> None:
        self._btn_coverage.setEnabled(enabled)

    def set_loading(self, loading: bool) -> None:
        self._btn_send.setEnabled(not loading)
        self._progress.setVisible(loading)
        if loading:
            self._set_status("PROCESANDO", "warning")

    # --- Datos ---------------------------------------------------------

    @staticmethod
    def _read_field(widget: QWidget) -> str:
        return widget.text().strip()

    @staticmethod
    def _write_field(widget: QWidget, value: str) -> None:
        if hasattr(widget, "set_text"):
            widget.set_text(value)
            return
        widget.setText(value)

    def sede(self) -> str | None:
        return self._sede_combo.currentData()

    def clear_sede(self) -> None:
        """Deja la SEDE sin seleccionar (tras guardar un registro)."""
        self._sede_combo.setCurrentIndex(0)

    def set_result(self, data: dict) -> None:
        """Rellena el formulario con el resultado de la IA."""
        self.set_form_data(data)
        self._set_status("DATOS OCR", "primary")

    def set_form_data(self, data: dict) -> None:
        """Rellena el formulario con datos (de la IA o restaurados del caché)."""
        self._destinatario_raw.setPlainText(data.get("destinatario_raw", "") or "")
        campos = data.get("campos") or {}
        for key, line in self._fields.items():
            self._write_field(line, campos.get(key, "") or "")
        self._observaciones.setPlainText(data.get("observaciones_ia", "") or "")
        if any(campos.values()) or data.get("destinatario_raw"):
            self._set_status("DATOS OCR", "primary")
            self._extraction_section.set_expanded(True)

    def get_form_data(self) -> dict:
        """Devuelve los datos del formulario para guardar."""
        return {
            "destinatario_raw": self._destinatario_raw.toPlainText().strip(),
            "campos": {key: self._read_field(line) for key, line in self._fields.items()},
            "observaciones_ia": self._observaciones.toPlainText().strip(),
        }

    def has_ocr_data(self) -> bool:
        """True si hay algo que guardar como registro OCR."""
        data = self.get_form_data()
        return bool(
            any(data["campos"].values())
            or data["destinatario_raw"]
            or data["observaciones_ia"]
        )

    def clear_form(self) -> None:
        self._destinatario_raw.clear()
        for line in self._fields.values():
            self._write_field(line, "")
        self._observaciones.clear()
        self._set_status("SIN DATOS", "neutral")
