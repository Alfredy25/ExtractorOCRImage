"""Buscador paginado de destinatarios, ficha y elección de domicilio."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QSize, Qt, Signal
from PySide6.QtGui import QIcon, QPainter, QPixmap, QWheelEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QComboBox,
    QDialog,
    QFrame,
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

from app.components.theme import COLOR, SPACE, icon_pixmap
from app.components.widgets import (
    chip,
    field_label,
    icon_label,
    section_label,
    set_property,
    subtitle,
    text_button,
)
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
    ("ID", "id"),
    ("Nombre", "full_name"),
    ("Organización", "name_org"),
    ("Fecha creacion", "created_at"),
)

_DIRECTION_OPTIONS = (
    ("Ascendente", "asc"),
    ("Descendente", "desc"),
)

# El servidor asigna uno de estos cuando el destinatario no tiene un cargo real.
_PLACEHOLDER_ROLE_ABBREVIATIONS = frozenset({
    "SIN CARGO",
    "INSTITUCIONAL GOBIERNO",
    "INSTITUCIONAL PRIVADO",
})


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


def _role_meaning(receiver: ReceiverDto) -> str:
    """Significado del cargo. Los marcadores del servidor no se muestran."""
    position = receiver.position
    if position is None or position.job_role is None:
        return ""
    abbreviation = position.job_role.abbreviation.strip().upper()
    if abbreviation in _PLACEHOLDER_ROLE_ABBREVIATIONS:
        return ""
    return position.job_role.meaning.strip()


def _organization_name(receiver: ReceiverDto) -> str:
    if receiver.position is None:
        return ""
    return receiver.position.organization.name.strip()


def _first_address_line(receiver: ReceiverDto) -> str:
    """Calle, número, colonia, estado y el código postal entre paréntesis."""
    if not receiver.addresses:
        return ""
    address = receiver.addresses[0]
    street = " ".join(
        part.strip()
        for part in (address.street, address.num_street)
        if part and part.strip()
    )
    parts = [
        part.strip()
        for part in (street, address.colony, address.state)
        if part and part.strip()
    ]
    line = ", ".join(parts)
    postal = (address.postal_code or "").strip()
    if postal:
        return f"{line} ({postal})" if line else f"({postal})"
    return line


def _type_tone(type_entity: str) -> str:
    if type_entity == "GOBIERNO":
        return "warning"
    if type_entity == "PRIVADA":
        return "neutral"
    return "primary"


def _address_count_text(count: int) -> str:
    noun = "domicilio" if count == 1 else "domicilios"
    return f"{count} {noun}"


def _address_count_badge(count: int) -> QFrame:
    """Recuadro con el icono y la cantidad de domicilios, sin el texto de alternos."""
    box = QFrame()
    box.setObjectName("receiverAddressCount")
    box.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    box.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
    layout = QHBoxLayout(box)
    layout.setContentsMargins(6, 2, 6, 2)
    layout.setSpacing(4)
    layout.addWidget(icon_label("apartment", size=12, role="mutedIcon"))
    label = QLabel(_address_count_text(count))
    label.setObjectName("receiverAddressCountText")
    layout.addWidget(label)
    return box


def _left_arrow_icon(size: int = 18) -> QIcon:
    """Flecha a la izquierda. La fuente solo trae la flecha hacia adelante."""
    source = icon_pixmap("arrow_forward", size, COLOR["on_surface_variant"])
    flipped = QPixmap(source.size())
    flipped.fill(Qt.GlobalColor.transparent)
    painter = QPainter(flipped)
    painter.translate(flipped.width(), 0)
    painter.scale(-1, 1)
    painter.drawPixmap(0, 0, source)
    painter.end()
    return QIcon(flipped)


def _icon_text_row(icon: str) -> tuple[QWidget, QLabel]:
    row = QWidget()
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(SPACE["xs"])
    layout.addWidget(icon_label(icon, size=14, role="mutedIcon"), 0, Qt.AlignmentFlag.AlignTop)
    label = subtitle("")
    label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
    layout.addWidget(label, 1)
    return row, label


def _heading(icon: str, text: str, trailing: QWidget | None = None) -> tuple[QWidget, QLabel]:
    label = section_label(text)
    label.setWordWrap(True)
    label.setMinimumWidth(0)
    label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
    row = QWidget()
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, SPACE["sm"], 0, 0)
    layout.setSpacing(SPACE["xs"])
    layout.addWidget(icon_label(icon, size=14, role="mutedIcon"), 0, Qt.AlignmentFlag.AlignVCenter)
    layout.addWidget(label, 1, Qt.AlignmentFlag.AlignVCenter)
    if trailing is not None:
        trailing.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        layout.addWidget(trailing, 0, Qt.AlignmentFlag.AlignVCenter)
    return row, label


def _icon_line(icon: str, text: str, object_name: str) -> QWidget:
    row = QWidget()
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(SPACE["xs"])
    layout.addWidget(icon_label(icon, size=14, role="mutedIcon"), 0, Qt.AlignmentFlag.AlignTop)
    label = subtitle(text)
    label.setObjectName(object_name)
    label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
    layout.addWidget(label, 1)
    return row


class _ReceiverResultCard(QFrame):
    """Tarjeta de un destinatario encontrado. El doble clic abre la ficha."""

    activated = Signal(int)

    def __init__(self, receiver: ReceiverDto, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("receiverResultCard")
        self._receiver_id = receiver.id
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

        root = QVBoxLayout(self)
        root.setContentsMargins(SPACE["sm"], SPACE["xs"], SPACE["sm"], SPACE["xs"])
        root.setSpacing(SPACE["xs"])

        header = QHBoxLayout()
        header.setSpacing(SPACE["xs"])
        kind = chip(receiver.type_entity, _type_tone(receiver.type_entity))
        kind.setObjectName("receiverResultType")
        kind.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        title = QLabel(receiver_display_name(receiver))
        title.setObjectName("receiverResultTitle")
        title.setProperty("role", "cardTitle")
        title.setWordWrap(True)
        title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        ident = chip(f"ID {receiver.id}", "neutral")
        ident.setObjectName("receiverResultId")
        ident.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        header.addWidget(kind, 0, Qt.AlignmentFlag.AlignTop)
        header.addWidget(title, 1, Qt.AlignmentFlag.AlignTop)
        header.addWidget(ident, 0, Qt.AlignmentFlag.AlignTop)
        root.addLayout(header)

        meaning = _role_meaning(receiver)
        if meaning:
            role = subtitle(meaning)
            role.setObjectName("receiverResultRole")
            root.addWidget(role)

        # En gobierno y privada el título ya es la organización.
        if receiver.type_entity == "PERSONA":
            organization = _organization_name(receiver)
            if organization:
                root.addWidget(_icon_line("apartment", organization, "receiverResultOrg"))

        footer = QHBoxLayout()
        footer.setSpacing(SPACE["xs"])
        address = _first_address_line(receiver)
        if address:
            footer.addWidget(_icon_line("place", address, "receiverResultAddress"), 1)
        else:
            footer.addStretch(1)
        footer.addWidget(_address_count_badge(len(receiver.addresses)), 0, Qt.AlignmentFlag.AlignTop)
        root.addLayout(footer)

    def mouseDoubleClickEvent(self, event) -> None:
        self.activated.emit(self._receiver_id)
        event.accept()


class _ReceiverResultList(QListWidget):
    """Lista de tarjetas. La altura de cada ítem sigue el ancho disponible."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("receiverResults")
        self._fitting = False
        self.setMinimumHeight(120)
        self.setMaximumHeight(320)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setSpacing(4)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

    def clear(self) -> None:
        super().clear()
        self.setMinimumHeight(120)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.fit_cards()

    def fit_cards(self) -> None:
        if self._fitting:
            return
        width = self.viewport().width()
        if width < 40 or self.count() == 0:
            return
        self._fitting = True
        try:
            total = 0
            for row in range(self.count()):
                item = self.item(row)
                card = self.itemWidget(item)
                if item is None or card is None:
                    continue
                height = card.heightForWidth(width)
                if height < 1:
                    height = card.sizeHint().height()
                total += height
                hint = QSize(width, height)
                if item.sizeHint() != hint:
                    item.setSizeHint(hint)
            gaps = self.spacing() * max(self.count() - 1, 0)
            frame = self.frameWidth() * 2 + 8
            wanted = min(self.maximumHeight(), max(120, total + gaps + frame))
            if self.minimumHeight() != wanted:
                self.setMinimumHeight(wanted)
        finally:
            self._fitting = False


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

        self._search_bar = QWidget()
        query_row = QHBoxLayout(self._search_bar)
        query_row.setContentsMargins(0, 0, 0, 0)
        query_row.setSpacing(SPACE["sm"])
        self._query = QLineEdit()
        self._query.setObjectName("receiverSearchInput")
        self._query.setPlaceholderText("Nombre de la persona o de la organización")
        self._query.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self._query.returnPressed.connect(self._on_search_clicked)
        self._btn_search = text_button("Buscar", variant="primary", icon="search")
        self._btn_search.clicked.connect(self._on_search_clicked)
        query_row.addWidget(self._query, 1)
        query_row.addWidget(self._btn_search)
        root.addWidget(self._search_bar)

        self._filters = self._build_filters()
        root.addWidget(self._filters)

        self._status = subtitle("")
        self._status.setVisible(False)
        root.addWidget(self._status)

        self._list = _ReceiverResultList()
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
            (self._labeled_combo("TIPO ENTIDAD", self._type_combo),
             self._labeled_combo("ESTADO", self._state_combo)),
            (self._labeled_combo("ORDENAR POR", self._order_combo),
             self._labeled_combo("ORDEN", self._direction_combo)),
        ):
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(SPACE["xs"])
            row.addWidget(left, 1)
            row.addWidget(right, 1)
            layout.addLayout(row)
        return box

    def _labeled_combo(self, caption: str, combo: QComboBox) -> QWidget:
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(field_label(caption))
        layout.addWidget(combo)
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
        ficha_layout.setContentsMargins(0, 0, 0, 0)
        ficha_layout.setSpacing(SPACE["xs"])

        header = QHBoxLayout()
        header.setSpacing(SPACE["xs"])
        self._type_chip = chip("", "primary")
        self._type_chip.setObjectName("receiverFichaType")
        self._type_chip.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._id_chip = chip("", "neutral")
        self._id_chip.setObjectName("receiverFichaId")
        self._id_chip.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._btn_edit = text_button("Editar", variant="ghost", icon="edit_document")
        self._btn_edit.setObjectName("receiverEditButton")
        self._btn_edit.clicked.connect(self._request_edit)
        header.addWidget(self._type_chip, 0, Qt.AlignmentFlag.AlignVCenter)
        header.addWidget(self._id_chip, 0, Qt.AlignmentFlag.AlignVCenter)
        header.addStretch(1)
        header.addWidget(self._btn_edit, 0, Qt.AlignmentFlag.AlignVCenter)
        ficha_layout.addLayout(header)

        self._name = QLabel("")
        self._name.setProperty("role", "cardTitle")
        self._name.setWordWrap(True)
        self._meta = subtitle("")
        email_row, self._email = _icon_text_row("mail")
        self._email.setObjectName("receiverFichaEmail")
        ficha_layout.addWidget(self._name)
        ficha_layout.addWidget(self._meta)
        ficha_layout.addWidget(email_row)

        phones, self._contacts_heading = _heading("phone", "Teléfonos registrados")
        ficha_layout.addWidget(phones)
        self._contacts = QVBoxLayout()
        self._contacts.setSpacing(SPACE["xs"])
        ficha_layout.addLayout(self._contacts)

        volantes, _volantes_label = _heading("description", "Volantes")
        ficha_layout.addWidget(volantes)
        self._volantes = QVBoxLayout()
        self._volantes.setSpacing(SPACE["xs"])
        ficha_layout.addLayout(self._volantes)
        self._btn_add_volante = text_button("Añadir nuevo volante", variant="ghost", icon="add")
        self._btn_add_volante.setObjectName("addVolanteButton")
        self._btn_add_volante.clicked.connect(self._open_volante)
        ficha_layout.addWidget(self._btn_add_volante, 0, Qt.AlignmentFlag.AlignLeft)

        self._btn_add_address = text_button("Registrar domicilio", variant="ghost", icon="add")
        self._btn_add_address.clicked.connect(self._open_address)
        addresses, _addresses_label = _heading("place", "Domicilios registrados", self._btn_add_address)
        ficha_layout.addWidget(addresses)
        self._addresses = QVBoxLayout()
        self._addresses.setSpacing(SPACE["xs"])
        ficha_layout.addLayout(self._addresses)

        hint_row, self._hint = _icon_text_row("info")
        self._hint.setText(
            "La colonia, el código postal, la ciudad y el estado del archivo "
            "de Paquetexpress salen de la cobertura. Este domicilio queda "
            "guardado en el destinatario."
        )
        ficha_layout.addWidget(hint_row)

        self._btn_change = text_button("Volver a buscar", variant="ghost")
        self._btn_change.setIcon(_left_arrow_icon())
        self._btn_change.setIconSize(QSize(18, 18))
        self._btn_change.clicked.connect(self._back_to_search)
        ficha_layout.addWidget(self._btn_change, 0, Qt.AlignmentFlag.AlignLeft)
        self._ficha.setVisible(False)
        return self._ficha

    def _set_search_visible(self, visible: bool) -> None:
        self._search_bar.setVisible(visible)
        self._filters.setVisible(visible)

    # --- Búsqueda ------------------------------------------------------

    def _on_search_clicked(self) -> None:
        self._search(1)

    def _on_filters_changed(self, _index: int) -> None:
        if self._searched:
            self._search(1)

    def _search(self, page: int) -> None:
        text = self._query.text().strip()
        self._receiver = None
        self._set_search_visible(True)
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
        self._set_status(f"{page.total} coincidencia(s). Doble clic abre la ficha.")
        for receiver in items:
            self._results[receiver.id] = receiver
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, receiver.id)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            card = _ReceiverResultCard(receiver)
            card.activated.connect(self._open_result)
            self._list.addItem(item)
            self._list.setItemWidget(item, card)
        self._list.fit_cards()

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

    def _open_result(self, receiver_id: int) -> None:
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
        self._set_search_visible(False)
        self._list.setVisible(False)
        self._pager.setVisible(False)
        self._ficha.setVisible(True)
        set_property(self._type_chip, "tone", _type_tone(receiver.type_entity))
        self._type_chip.setText(receiver.type_entity)
        self._id_chip.setText(f"ID {receiver.id}")
        self._name.setText(receiver_display_name(receiver))
        position = receiver_position_line(receiver)
        self._meta.setText(position)
        self._meta.setVisible(bool(position))
        self._email.setText(receiver.email or "Sin correo")
        self._rebuild_contacts(receiver, preferred_contact_id)
        self._rebuild_volantes(receiver)
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
        self._contacts_heading.setText(f"TELÉFONOS REGISTRADOS ({len(contacts)})")

        if not contacts:
            self._selected_contact = None
            empty = subtitle("Sin teléfonos")
            empty.setObjectName("receiverContactEmpty")
            self._contacts.addWidget(empty)
            return

        chosen = preferred_contact_id
        if chosen is None or all(item.id != chosen for item in contacts):
            chosen = contacts[0].id
        selected = next((item for item in contacts if item.id == chosen), contacts[0])
        self._selected_contact = selected

        if len(contacts) > 1:
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

        line = subtitle(contact_display_line(selected))
        line.setObjectName("receiverContactLine")
        self._contacts.addWidget(line)

    def _rebuild_volantes(self, receiver: ReceiverDto) -> None:
        while self._volantes.count():
            item = self._volantes.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        if not receiver.volantes:
            empty = subtitle("Sin volantes")
            empty.setObjectName("receiverVolanteEmpty")
            self._volantes.addWidget(empty)
            return
        for volante in receiver.volantes:
            self._volantes.addWidget(_icon_line("description", volante.name, "receiverVolanteItem"))

    def _open_volante(self) -> None:
        if self._receiver is None:
            return
        from app.views.volante_dialog import VolanteDialog

        dialog = VolanteDialog(self._receiver.id, parent=self.window())
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        created = dialog.created_volante
        if created is None:
            return
        volantes = [item for item in self._receiver.volantes if item.id != created.id]
        volantes.append(created)
        address_id = self._address_group.checkedId()
        contact_id = self._selected_contact.id if self._selected_contact is not None else None
        self._receiver = self._receiver.model_copy(update={"volantes": volantes})
        self.show_receiver(
            self._receiver,
            address_id if address_id >= 0 else None,
            contact_id,
        )

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
        self._set_search_visible(True)
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
        self._set_search_visible(True)
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
