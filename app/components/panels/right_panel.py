"""Inspector de extracción: sede, campos OCR editables y acciones del registro.

Mantiene el contrato de datos anterior (``get_form_data`` / ``set_form_data`` con
las claves de ``FIELD_KEYS``) y añade el selector de SEDE, que antes vivía en el
panel izquierdo.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLineEdit,
    QProgressBar,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.components.theme import SPACE
from app.components.widgets import (
    Card,
    chip,
    divider,
    icon_label,
    labeled_field,
    section_label,
    text_button,
)
from app.config import SEDES
from app.models.field_schema import FIELD_KEYS

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
    ("Control interno", "numbers", [["numero_volante", "extras"]]),
]


class RightPanel(Card):
    """Tarjeta lateral con el formulario de extracción y sus acciones."""

    send_to_ai_clicked = Signal()
    check_coverage_clicked = Signal()
    save_clicked = Signal()
    sede_changed = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__("Datos extraídos", "data_object", parent)
        self._fields: dict[str, QLineEdit] = {}
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
        layout = QVBoxLayout(content)
        layout.setContentsMargins(SPACE["md"], SPACE["md"], SPACE["md"], SPACE["md"])
        layout.setSpacing(SPACE["md"])

        layout.addWidget(self._build_sede_section())

        placed: set[str] = set()
        for title, icon, rows in SECTIONS:
            keys = [key for row in rows for key in row if key in FIELD_KEYS]
            if not keys:
                continue
            placed.update(keys)
            layout.addWidget(self._build_field_section(title, icon, rows))

        # Red de seguridad: si FIELD_KEYS crece, el campo nuevo sigue apareciendo.
        leftover = [key for key in FIELD_KEYS if key not in placed]
        if leftover:
            layout.addWidget(
                self._build_field_section("Otros datos", "tune", [[key] for key in leftover])
            )

        layout.addWidget(self._build_raw_section())
        layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(content)
        return scroll

    def _build_sede_section(self) -> QFrame:
        box, layout = self._section_box("Ubicación", "apartment")
        self._sede_combo = QComboBox()
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
        line = QLineEdit()
        line.setPlaceholderText("—")
        self._fields[key] = line
        label = FIELD_LABELS.get(key, key.replace("_", " ").capitalize())
        return labeled_field(label, line, mono=key in MONO_FIELDS)

    def _build_raw_section(self) -> QFrame:
        box, layout = self._section_box("Texto OCR", "description")

        self._destinatario_raw = QTextEdit()
        self._destinatario_raw.setMaximumHeight(90)
        self._destinatario_raw.setProperty("role", "mono")
        layout.addWidget(labeled_field("Texto bruto (destinatario_raw)", self._destinatario_raw))

        self._observaciones = QTextEdit()
        self._observaciones.setMaximumHeight(80)
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

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)  # Indeterminado: no conocemos la duración
        self._progress.setTextVisible(False)
        self._progress.hide()
        layout.addWidget(self._progress)

        self._btn_send = text_button("Enviar a IA", variant="primary", icon="auto_awesome")
        self._btn_send.setMinimumHeight(38)
        self._btn_send.clicked.connect(self.send_to_ai_clicked.emit)
        layout.addWidget(self._btn_send)

        # Botones apilados a todo el ancho, como en el diseño de referencia: en una
        # sola fila las etiquetas no caben en el ancho del inspector y se recortan.
        self._btn_coverage = text_button(
            "Consultar cobertura", variant="ghost", icon="local_shipping"
        )
        self._btn_coverage.setMinimumHeight(34)
        self._btn_coverage.clicked.connect(self.check_coverage_clicked.emit)
        layout.addWidget(self._btn_coverage)

        self._btn_save = text_button("Guardar registro", variant="primary", icon="save")
        self._btn_save.setMinimumHeight(34)
        self._btn_save.clicked.connect(self.save_clicked.emit)
        layout.addWidget(self._btn_save)
        return footer

    # --- Estado --------------------------------------------------------

    def _set_status(self, text: str, tone: str) -> None:
        self._status_chip.setText(text)
        self._status_chip.setProperty("tone", tone)
        style = self._status_chip.style()
        style.unpolish(self._status_chip)
        style.polish(self._status_chip)

    def set_send_enabled(self, enabled: bool) -> None:
        self._btn_send.setEnabled(enabled)

    def set_loading(self, loading: bool) -> None:
        self._btn_send.setEnabled(not loading)
        self._progress.setVisible(loading)
        if loading:
            self._set_status("PROCESANDO", "warning")

    # --- Datos ---------------------------------------------------------

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
            line.setText(campos.get(key, "") or "")
        self._observaciones.setPlainText(data.get("observaciones_ia", "") or "")
        if any(campos.values()) or data.get("destinatario_raw"):
            self._set_status("DATOS OCR", "primary")

    def get_form_data(self) -> dict:
        """Devuelve los datos del formulario para guardar."""
        return {
            "destinatario_raw": self._destinatario_raw.toPlainText().strip(),
            "campos": {key: line.text().strip() for key, line in self._fields.items()},
            "observaciones_ia": self._observaciones.toPlainText().strip(),
        }

    def clear_form(self) -> None:
        self._destinatario_raw.clear()
        for line in self._fields.values():
            line.clear()
        self._observaciones.clear()
        self._set_status("SIN DATOS", "neutral")
