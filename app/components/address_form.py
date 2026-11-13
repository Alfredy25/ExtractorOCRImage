"""Formulario de domicilio con consulta SEPOMEX por código postal."""

from __future__ import annotations

import re
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from app.components.theme import SPACE
from app.components.widgets import labeled_field, subtitle, text_button
from app.models.receiver import ESTADOS_MX, match_estado
from app.models.sepomex import SepomexDto
from app.services import sepomex_service
from app.utils.normalizers import normalize_street
from app.states.workers.callable_worker import run_worker
from app.views.session_relogin import prompt_relogin_after_session_expired


class _NoWheelComboBox(QComboBox):
    def wheelEvent(self, event: QWheelEvent) -> None:
        event.ignore()


class AddressFormWidget(QWidget):
    """Calle, número y datos que SEPOMEX puede rellenar a partir del C.P."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._rows: list[SepomexDto] = []
        self._looked_up = ""

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(SPACE["sm"])

        self._street = QLineEdit()
        self._street.setPlaceholderText("Av. Hidalgo")
        self._num = QLineEdit()
        self._num.setPlaceholderText("123 o SN")
        self._num.setMaxLength(15)

        street_row = QHBoxLayout()
        street_row.setSpacing(SPACE["sm"])
        street_row.addWidget(labeled_field("Calle", self._street), 3)
        street_row.addWidget(labeled_field("Número", self._num), 1)
        root.addLayout(street_row)

        self._cp = QLineEdit()
        self._cp.setMaxLength(5)
        self._cp.setPlaceholderText("97000")
        self._cp.editingFinished.connect(self.lookup_postal_code)
        self._cp.textEdited.connect(lambda _text: self._mark_cp_dirty())
        consult = text_button("Consultar", variant="ghost", icon="search")
        consult.clicked.connect(self.lookup_postal_code)
        cp_row = QHBoxLayout()
        cp_row.setSpacing(SPACE["sm"])
        cp_row.addWidget(labeled_field("Código postal", self._cp, mono=True), 1)
        cp_row.addWidget(consult, 0, Qt.AlignmentFlag.AlignBottom)
        root.addLayout(cp_row)

        self._status = subtitle("")
        self._status.setVisible(False)
        root.addWidget(self._status)

        self._colony = _NoWheelComboBox()
        self._colony.setEditable(True)
        self._colony.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self._colony.currentIndexChanged.connect(self._on_colony_changed)
        root.addWidget(labeled_field("Colonia", self._colony))

        self._municipality = QLineEdit()
        self._city = QLineEdit()
        geo = QGridLayout()
        geo.setHorizontalSpacing(SPACE["sm"])
        geo.setVerticalSpacing(SPACE["sm"])
        geo.addWidget(labeled_field("Municipio", self._municipality), 0, 0)
        geo.addWidget(labeled_field("Ciudad", self._city), 0, 1)
        root.addLayout(geo)

        self._state = _NoWheelComboBox()
        self._state.addItem("Seleccione", "")
        for estado in ESTADOS_MX:
            self._state.addItem(estado, estado)
        self._country = QLineEdit("MEXICO")
        place = QHBoxLayout()
        place.setSpacing(SPACE["sm"])
        place.addWidget(labeled_field("Estado", self._state), 1)
        place.addWidget(labeled_field("País", self._country), 1)
        root.addLayout(place)

        self._reference = QLineEdit()
        self._reference.setPlaceholderText("Edificio, piso, ventanilla…")
        self._reference.setMaxLength(50)
        root.addWidget(labeled_field("Referencia de entrega", self._reference))

    def normalize_street_and_number(self) -> None:
        """Abrevia calle y número con la misma regla."""
        self._street.setText(normalize_street(self._street.text()))
        self._num.setText(normalize_street(self._num.text()))

    def set_from_address(self, address) -> None:
        """Precarga un domicilio ya guardado y, si hay C.P., consulta SEPOMEX."""
        self._street.setText(address.street)
        self._num.setText(address.num_street)
        self._colony.setEditText(address.colony)
        self._municipality.setText(address.municipality)
        self._city.setText(address.city)
        self._set_state(address.state)
        self._cp.setText(address.postal_code)
        self._country.setText(address.country or "MEXICO")
        self._reference.setText(address.address_reference or "")
        self._looked_up = ""
        self.lookup_postal_code()

    def set_initial_from_ocr(self, campos: dict[str, Any]) -> None:
        """Copia la dirección leída del sobre y, si hay C.P., consulta SEPOMEX."""
        self._street.setText(str(campos.get("direccion") or "").strip())
        self._colony.setEditText(str(campos.get("colonia") or "").strip())
        municipio = str(campos.get("municipio_alcaldia") or "").strip()
        self._municipality.setText(municipio)
        self._city.setText(municipio)
        self._set_state(str(campos.get("estado") or ""))
        self._reference.setText(str(campos.get("indicaciones") or "").strip())
        self._cp.setText(str(campos.get("codigo_postal") or "").strip())
        self._looked_up = ""
        self.lookup_postal_code()

    def get_payload(self) -> dict[str, Any]:
        reference = self._reference.text().strip()
        return {
            "street": self._street.text().strip(),
            "num_street": self._num.text().strip(),
            "colony": self._colony.currentText().strip(),
            "municipality": self._municipality.text().strip(),
            "city": self._city.text().strip(),
            "state": str(self._state.currentData() or ""),
            "postal_code": self._cp.text().strip(),
            "country": self._country.text().strip() or "MEXICO",
            "address_reference": reference or None,
        }

    def lookup_postal_code(self) -> None:
        cp = self._cp.text().strip()
        if not re.fullmatch(r"\d{5}", cp):
            if cp:
                self._set_status("El código postal debe tener 5 dígitos.")
            return
        if cp == self._looked_up:
            return
        self._looked_up = cp
        self._set_status("Consultando SEPOMEX…")
        run_worker(
            self,
            lambda: sepomex_service.fetch_sepomex(cp),
            lambda rows, current=cp: self._on_rows(current, rows),
            lambda exc, current=cp: self._on_fail(current, exc),
        )

    def _mark_cp_dirty(self) -> None:
        self._looked_up = ""

    def _on_rows(self, cp: str, rows: list[SepomexDto]) -> None:
        if cp != self._cp.text().strip():
            return
        if not rows:
            self._set_status("Ese código postal no está en SEPOMEX. Capture el domicilio a mano.")
            return
        wanted = self._colony.currentText().strip().upper()
        self._rows = list(rows)
        match_index = 0
        self._colony.blockSignals(True)
        typed = self._colony.currentText()
        self._colony.clear()
        for index, row in enumerate(self._rows):
            self._colony.addItem(row.settlement, index)
            if wanted and row.settlement.upper() == wanted:
                match_index = index
        self._colony.setCurrentIndex(match_index)
        self._colony.blockSignals(False)
        if wanted and self._rows[match_index].settlement.upper() != wanted:
            self._colony.setEditText(typed)
        self._apply_row(self._rows[match_index])
        count = len(self._rows)
        noun = "asentamiento" if count == 1 else "asentamientos"
        self._set_status(f"SEPOMEX: {count} {noun}.")

    def _on_fail(self, cp: str, exc: Exception) -> None:
        if cp != self._cp.text().strip():
            return
        self._looked_up = ""
        if isinstance(exc, sepomex_service.SepomexNotFoundError):
            self._set_status("Ese código postal no está en SEPOMEX. Capture el domicilio a mano.")
            return
        if isinstance(exc, sepomex_service.SepomexSessionExpiredError):
            self._set_status("")
            prompt_relogin_after_session_expired(self, str(exc))
            return
        self._set_status(str(exc))

    def _on_colony_changed(self, index: int) -> None:
        data = self._colony.itemData(index)
        if isinstance(data, int) and 0 <= data < len(self._rows):
            self._apply_row(self._rows[data])

    def _apply_row(self, row: SepomexDto) -> None:
        self._municipality.setText(row.municipality or "")
        city = (row.city or "").strip() or (row.municipality or "").strip()
        self._city.setText(city)
        self._set_state(row.state)

    def _set_state(self, value: str) -> None:
        matched = match_estado(value)
        if matched is None:
            return
        index = self._state.findData(matched)
        if index >= 0:
            self._state.setCurrentIndex(index)

    def _set_status(self, text: str) -> None:
        self._status.setText(text)
        self._status.setVisible(bool(text))
