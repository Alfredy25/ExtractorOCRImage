"""Buscador paginado de destinatarios, ficha y elección de domicilio."""

from __future__ import annotations

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QRadioButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.components.theme import SPACE
from app.components.widgets import subtitle, text_button
from app.models.receiver import (
    ESTADOS_MX,
    AddressDto,
    ContactDto,
    ReceiverDto,
    contact_display_line,
    receiver_display_name,
    receiver_position_line,
)
from app.services import receivers_service
from app.states.workers.callable_worker import run_worker
from app.views.session_relogin import prompt_relogin_after_session_expired

# Arranque que fija el flujo: página 1, 10 por página, id ascendente.
PAGE_SIZE = 10

_TYPE_OPTIONS = (
    ("Todos los tipos", None),
    ("PERSONA", "PERSONA"),
    ("GOBIERNO", "GOBIERNO"),
    ("PRIVADA", "PRIVADA"),
)

_ORDER_OPTIONS = (
    ("Ordenar por ID", "id"),
    ("Ordenar por nombre", "full_name"),
    ("Ordenar por organización", "name_org"),
    ("Ordenar por alta", "created_at"),
)

_DIRECTION_OPTIONS = (
    ("Ascendente", "asc"),
    ("Descendente", "desc"),
)


class _NoWheelComboBox(QComboBox):
    """La rueda del ratón no cambia el valor; el padre puede seguir haciendo scroll."""

    def wheelEvent(self, event: QWheelEvent) -> None:
        event.ignore()


class _WrappingRadio(QWidget):
    """Radio con texto largo que baja de línea en el Inspector estrecho."""

    def __init__(self, text: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.button = QRadioButton()
        self.button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        label = QLabel(text)
        label.setWordWrap(True)
        label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        label.setToolTip(text)
        label.installEventFilter(self)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(SPACE["xs"])
        row.addWidget(self.button, 0, Qt.AlignmentFlag.AlignTop)
        row.addWidget(label, 1)

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.MouseButtonRelease:
            self.button.click()
            return True
        return super().eventFilter(watched, event)


def _address_label(address: AddressDto) -> str:
    reference = f" · {address.address_reference}" if address.address_reference else ""
    return (
        f"{address.street} {address.num_street}, {address.colony}, "
        f"{address.city}, {address.state} C.P. {address.postal_code}{reference}"
    )


class ReceiverPicker(QWidget):
    """Estado de búsqueda o ficha del destinatario elegido."""

    receiver_selected = Signal(object, object)
    selection_cleared = Signal()
    empty_results = Signal()
    edit_requested = Signal(object)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("ReceiverPicker")
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self._receiver: ReceiverDto | None = None
        self._results: dict[int, ReceiverDto] = {}
        self._searched = False
        self._page = 1
        self._total_pages = 0
        self._selected_contact: ContactDto | None = None
        self._address_group = QButtonGroup(self)
        self._address_group.setExclusive(True)
        self._address_group.idToggled.connect(self._on_address_toggled)
        self._contact_group = QButtonGroup(self)
        self._contact_group.setExclusive(True)
        self._contact_group.idToggled.connect(self._on_contact_toggled)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(SPACE["sm"])

        self._query = QLineEdit()
        self._query.setObjectName("receiverSearchInput")
        self._query.setPlaceholderText("Nombre de la persona o de la organización")
        self._query.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self._query.returnPressed.connect(self._on_search_clicked)
        self._btn_search = text_button("Buscar", variant="primary", icon="search")
        self._btn_search.clicked.connect(self._on_search_clicked)
        query_row = QHBoxLayout()
        query_row.setSpacing(SPACE["sm"])
        query_row.addWidget(self._query, 1)
        query_row.addWidget(self._btn_search)
        root.addLayout(query_row)

        root.addWidget(self._build_filters())

        self._status = subtitle("")
        self._status.setVisible(False)
        root.addWidget(self._status)

        self._list = QListWidget()
        self._list.setObjectName("receiverResults")
        self._list.setMinimumHeight(120)
        self._list.setMaximumHeight(200)
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list.setTextElideMode(Qt.TextElideMode.ElideRight)
        self._list.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self._list.itemClicked.connect(self._on_result_clicked)
        root.addWidget(self._list)

        root.addWidget(self._build_pagination())
        root.addWidget(self._build_ficha())

    # --- Construcción --------------------------------------------------

    def _build_filters(self) -> QWidget:
        """Filtros y orden opcionales del contrato de `GET /receivers/`."""
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACE["xs"])

        self._type_combo = self._combo(_TYPE_OPTIONS)
        self._state_combo = self._combo(
            (("Todos los estados", None), *((estado, estado) for estado in ESTADOS_MX))
        )
        self._order_combo = self._combo(_ORDER_OPTIONS)
        self._direction_combo = self._combo(_DIRECTION_OPTIONS)

        for left, right in (
            (self._type_combo, self._state_combo),
            (self._order_combo, self._direction_combo),
        ):
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(SPACE["xs"])
            row.addWidget(left, 1)
            row.addWidget(right, 1)
            layout.addLayout(row)
        return box

    def _combo(self, options) -> QComboBox:
        combo = _NoWheelComboBox()
        for label, value in options:
            combo.addItem(label, value)
        # El combo no debe pedir el ancho del estado más largo: si no, el
        # Inspector se recorta porque el scroll horizontal está apagado.
        combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        combo.setMinimumContentsLength(8)
        combo.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        # Cambiar un filtro repite la búsqueda desde la primera página, pero
        # solo si ya hay una consulta hecha: si no, no hay texto que buscar.
        combo.currentIndexChanged.connect(self._on_filters_changed)
        return combo

    def _build_pagination(self) -> QWidget:
        self._pager = QWidget()
        layout = QHBoxLayout(self._pager)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACE["sm"])

        self._btn_prev = text_button("Anterior", variant="ghost")
        self._btn_prev.clicked.connect(lambda: self._search(self._page - 1))
        self._page_label = subtitle("")
        self._page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._btn_next = text_button("Siguiente", variant="ghost")
        self._btn_next.clicked.connect(lambda: self._search(self._page + 1))

        layout.addWidget(self._btn_prev)
        layout.addWidget(self._page_label, 1)
        layout.addWidget(self._btn_next)
        self._pager.setVisible(False)
        return self._pager

    def _build_ficha(self) -> QWidget:
        self._ficha = QWidget()
        ficha_layout = QVBoxLayout(self._ficha)
        ficha_layout.setContentsMargins(0, SPACE["sm"], 0, 0)
        ficha_layout.setSpacing(SPACE["xs"])
        self._name = QLabel("")
        self._name.setProperty("role", "cardTitle")
        self._name.setWordWrap(True)
        self._meta = subtitle("")
        self._contact_summary = subtitle("")
        ficha_layout.addWidget(self._name)
        ficha_layout.addWidget(self._meta)
        ficha_layout.addWidget(self._contact_summary)

        self._contacts_heading = subtitle("Teléfonos registrados")
        self._contacts_heading.setVisible(False)
        ficha_layout.addWidget(self._contacts_heading)
        self._contacts = QVBoxLayout()
        self._contacts.setSpacing(SPACE["xs"])
        ficha_layout.addLayout(self._contacts)

        self._btn_edit = text_button("Editar destinatario", variant="ghost", icon="edit_document")
        self._btn_edit.setObjectName("receiverEditButton")
        self._btn_edit.clicked.connect(self._request_edit)
        ficha_layout.addWidget(self._btn_edit, 0, Qt.AlignmentFlag.AlignLeft)

        ficha_layout.addWidget(subtitle("Domicilios registrados"))
        self._btn_add_address = text_button("Registrar domicilio", variant="ghost", icon="add")
        self._btn_add_address.clicked.connect(self._open_address)
        ficha_layout.addWidget(self._btn_add_address, 0, Qt.AlignmentFlag.AlignLeft)

        self._addresses = QVBoxLayout()
        self._addresses.setSpacing(SPACE["xs"])
        ficha_layout.addLayout(self._addresses)

        self._hint = subtitle(
            "La colonia, el código postal, la ciudad y el estado del archivo "
            "de Paquetexpress salen de la cobertura. Este domicilio queda "
            "guardado en el destinatario."
        )
        ficha_layout.addWidget(self._hint)

        self._btn_change = text_button("Cambiar destinatario", variant="ghost", icon="search")
        self._btn_change.clicked.connect(self._back_to_search)
        ficha_layout.addWidget(self._btn_change, 0, Qt.AlignmentFlag.AlignLeft)
        self._ficha.setVisible(False)
        return self._ficha

    # --- Búsqueda ------------------------------------------------------

    def _on_search_clicked(self) -> None:
        self._search(1)

    def _on_filters_changed(self, _index: int) -> None:
        if self._searched:
            self._search(1)

    def _search(self, page: int) -> None:
        text = self._query.text().strip()
        self._receiver = None
        self._ficha.setVisible(False)
        self._list.setVisible(True)
        self.selection_cleared.emit()
        self._set_status("Buscando…")
        self._list.clear()
        self._results.clear()
        self._pager.setVisible(False)
        run_worker(
            self,
            lambda: receivers_service.search_receivers(
                text,
                type_entity=self._type_combo.currentData(),
                state=self._state_combo.currentData(),
                page=max(1, page),
                page_size=PAGE_SIZE,
                order_by=self._order_combo.currentData(),
                direction=self._direction_combo.currentData(),
            ),
            self._on_results,
            self._on_search_failed,
        )

    def _on_results(self, page) -> None:
        self._searched = True
        self._page = page.page
        self._total_pages = page.total_pages
        self._list.clear()
        self._results.clear()
        self._update_pager(page)
        items = list(page.items)
        if not items:
            self._set_status(
                "Sin coincidencias. Extraiga los datos de la foto para continuar "
                "por la rama de alta."
            )
            self.empty_results.emit()
            return
        self._set_status(f"{page.total} coincidencia(s).")
        for receiver in items:
            self._results[receiver.id] = receiver
            label = receiver_display_name(receiver)
            position = receiver_position_line(receiver)
            kind = receiver.type_entity
            text = f"{kind} · {label}"
            if position and position != label:
                text = f"{text} · {position}"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, receiver.id)
            item.setToolTip(receiver.email or "")
            self._list.addItem(item)

    def _update_pager(self, page) -> None:
        total_pages = max(page.total_pages, 1)
        self._page_label.setText(
            f"Página {page.page} de {total_pages} · {page.total} resultado(s)"
        )
        self._btn_prev.setEnabled(page.has_prev)
        self._btn_next.setEnabled(page.has_next)
        self._pager.setVisible(page.has_prev or page.has_next)

    def _on_search_failed(self, exc: Exception) -> None:
        self._pager.setVisible(False)
        if isinstance(exc, receivers_service.ReceiverSessionExpiredError):
            self._set_status("")
            prompt_relogin_after_session_expired(self, str(exc))
            return
        if isinstance(exc, receivers_service.ReceiverValidationError) and exc.errors:
            self._set_status(exc.errors[0]["error"])
            return
        self._set_status(str(exc))

    def _on_result_clicked(self, item: QListWidgetItem) -> None:
        receiver_id = item.data(Qt.ItemDataRole.UserRole)
        receiver = self._results.get(int(receiver_id))
        if receiver is None:
            return
        preferred = receiver.addresses[0].id if receiver.addresses else None
        self.show_receiver(receiver, preferred)

    # --- Ficha ---------------------------------------------------------

    def show_receiver(
        self,
        receiver: ReceiverDto,
        preferred_address_id: int | None,
        preferred_contact_id: int | None = None,
    ) -> None:
        """Muestra la ficha y deja elegido un domicilio si existe."""
        same = self._receiver is not None and self._receiver.id == receiver.id
        if preferred_contact_id is None and same and self._selected_contact is not None:
            preferred_contact_id = self._selected_contact.id
        self._receiver = receiver
        self._list.setVisible(False)
        self._pager.setVisible(False)
        self._ficha.setVisible(True)
        self._name.setText(receiver_display_name(receiver))
        position = receiver_position_line(receiver)
        self._meta.setText(position or receiver.type_entity)
        self._rebuild_contacts(receiver, preferred_contact_id)
        self._rebuild_addresses(receiver, preferred_address_id)
        if not receiver.addresses:
            self._set_status("Este destinatario no tiene domicilios. Registre uno.")
            self.selection_cleared.emit()

    def selected_contact(self) -> ContactDto | None:
        return self._selected_contact

    def _rebuild_addresses(self, receiver: ReceiverDto, preferred_address_id: int | None) -> None:
        for button in self._address_group.buttons():
            self._address_group.removeButton(button)
        while self._addresses.count():
            item = self._addresses.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        if not receiver.addresses:
            return
        chosen = preferred_address_id
        if chosen is None or all(addr.id != chosen for addr in receiver.addresses):
            chosen = receiver.addresses[0].id
        self._address_group.blockSignals(True)
        for address in receiver.addresses:
            choice = _WrappingRadio(_address_label(address))
            self._address_group.addButton(choice.button, address.id)
            self._addresses.addWidget(choice)
            if address.id == chosen:
                choice.button.setChecked(True)
        self._address_group.blockSignals(False)
        self._emit_address(chosen)

    def _rebuild_contacts(
        self, receiver: ReceiverDto, preferred_contact_id: int | None
    ) -> None:
        for button in self._contact_group.buttons():
            self._contact_group.removeButton(button)
        while self._contacts.count():
            item = self._contacts.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        contacts = list(receiver.contacts)
        many = len(contacts) > 1
        self._contacts_heading.setVisible(many)

        if not contacts:
            self._selected_contact = None
            bits = [receiver.email or ""]
            self._contact_summary.setText(bits[0] if bits[0] else "Sin correo ni teléfono")
            return

        chosen = preferred_contact_id
        if chosen is None or all(item.id != chosen for item in contacts):
            chosen = contacts[0].id
        selected = next((item for item in contacts if item.id == chosen), contacts[0])
        self._selected_contact = selected

        email = receiver.email or ""
        if many:
            self._contact_summary.setText(email or "Sin correo")
            self._contact_group.blockSignals(True)
            for item in contacts:
                choice = _WrappingRadio(contact_display_line(item))
                choice.setObjectName("receiverContactChoice")
                self._contact_group.addButton(choice.button, item.id)
                self._contacts.addWidget(choice)
                if item.id == chosen:
                    choice.button.setChecked(True)
            self._contact_group.blockSignals(False)
            return

        phone = contact_display_line(selected)
        bits = [bit for bit in (email, phone) if bit]
        self._contact_summary.setText(" · ".join(bits) if bits else "Sin correo ni teléfono")

    def _on_contact_toggled(self, contact_id: int, checked: bool) -> None:
        if not checked or self._receiver is None:
            return
        match = next((item for item in self._receiver.contacts if item.id == contact_id), None)
        if match is not None:
            self._selected_contact = match

    def _on_address_toggled(self, address_id: int, checked: bool) -> None:
        if checked:
            self._emit_address(address_id)

    def _emit_address(self, address_id: int) -> None:
        if self._receiver is None:
            return
        address = next((item for item in self._receiver.addresses if item.id == address_id), None)
        if address is None:
            self.selection_cleared.emit()
            return
        self._set_status("")
        self.receiver_selected.emit(self._receiver, address)

    def _back_to_search(self) -> None:
        self._receiver = None
        self._selected_contact = None
        self._ficha.setVisible(False)
        self._list.setVisible(True)
        self._pager.setVisible(self._total_pages > 1)
        self.selection_cleared.emit()

    def reset(self) -> None:
        """Deja el buscador como al abrir una imagen nueva."""
        self._receiver = None
        self._selected_contact = None
        self._results.clear()
        self._searched = False
        self._page = 1
        self._total_pages = 0
        self._query.clear()
        self._list.clear()
        self._list.setVisible(True)
        self._ficha.setVisible(False)
        self._pager.setVisible(False)
        self._set_status("")
        self.selection_cleared.emit()

    def _request_edit(self) -> None:
        if self._receiver is None:
            return
        self.edit_requested.emit(self._receiver)

    def _open_address(self) -> None:
        if self._receiver is None:
            return
        from app.views.address_dialog import AddressDialog

        dialog = AddressDialog(self._receiver.id, parent=self.window())
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        if dialog.created_address is not None:
            addresses = [*self._receiver.addresses, dialog.created_address]
            self._receiver = self._receiver.model_copy(update={"addresses": addresses})
            self.show_receiver(self._receiver, dialog.created_address.id)
            return
        if dialog.duplicate_address_id is None:
            return
        match = next(
            (item for item in self._receiver.addresses if item.id == dialog.duplicate_address_id),
            None,
        )
        if match is not None:
            self.show_receiver(self._receiver, match.id)
            return
        QMessageBox.information(
            self,
            "Domicilio existente",
            "Ese domicilio ya estaba registrado, pero no viene en la ficha cargada. "
            "Vuelva a buscar al destinatario para verlo.",
        )

    def _set_status(self, text: str) -> None:
        self._status.setText(text)
        self._status.setVisible(bool(text))
