"""Ventana de captura y envío Paquetexpress."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QPixmap, QWheelEvent
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDoubleSpinBox, QFrame, QGridLayout, QHBoxLayout,QLabel,
    QLineEdit, QMessageBox, QScrollArea, QSizePolicy, QSpinBox, QTextEdit, QVBoxLayout, QWidget,
)

from app.components.theme import COLOR, FONT_SIZE, SPACE, mono_font, qicon
from app.components.widgets import (
    Banner, Card, divider, icon_label,
    labeled_field, section_label, subtitle, text_button,
)
from app.models.receiver import (
    AddressDto, ContactDto, ReceiverDto, contact_display_line,
    receiver_display_name, receiver_position_line, shipment_receiver_name,
)
from app.models.shipping import CoverageItem, ShippingDto
from app.services.paquetexpress_service import (
    DEFAULT_SHIPMENT_EMAIL,
    PaquetexpressCoverageNotFoundError,
    PaquetexpressServiceError,PaquetexpressSessionExpiredError,
    PaquetexpressValidationError, build_shipment_draft,
    build_shipment_payload_from_receiver, create_shipment,
    get_coverages_for_postal_code, update_shipment,
)
from app.utils.image_io import np_to_qpixmap
from app.utils.normalizers import normalize_email, normalize_shipment_fields
from app.views.session_relogin import prompt_relogin_after_session_expired

# Campos con datos técnicos: se muestran en monoespaciada para facilitar el
# cotejo carácter a carácter contra la etiqueta del sobre.
_MONO_KEYS = {"rfc", "phone", "num_street", "package_code", "quantity", "weight", "length", "width", "height",}
_COUNTED_KEYS = {"name_receiver", "street", "num_street", "address_reference"}


class _IgnoreWheelMixin:
    """Deja pasar la rueda al scroll del formulario en lugar de cambiar el valor."""

    def wheelEvent(self, event: QWheelEvent) -> None:
        event.ignore()


class _NoWheelSpinBox(_IgnoreWheelMixin, QSpinBox):
    pass


class _NoWheelDoubleSpinBox(_IgnoreWheelMixin, QDoubleSpinBox):
    pass


class _NoWheelComboBox(_IgnoreWheelMixin, QComboBox):
    pass


class _CropPreview(QLabel):
    """Imagen del recorte ajustada al ancho de su columna, sin deformarla.

    La política ``Ignored`` evita que el tamaño del pixmap arrastre al layout:
    manda la columna y la imagen se reescala detrás.
    """

    def __init__(self, pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self._source = pixmap
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumHeight(260)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self._rescale(QSize(420, 620))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._rescale(self.size())

    def _rescale(self, size: QSize) -> None:
        if self._source.isNull() or size.width() <= 0 or size.height() <= 0:
            return
        self.setPixmap(
            self._source.scaled(
                size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )


def preferred_coverage_index(coverages: list[CoverageItem], colony: str) -> int:
    """Índice de la colonia del domicilio guardado, o la primera si no coincide."""
    target = colony.strip().upper()
    for index, item in enumerate(coverages):
        if item.colony.strip().upper() == target:
            return index
    return 0


def _address_summary(address: AddressDto) -> str:
    """Domicilio en una línea, como se ve en la ficha del Workspace."""
    reference = f" · {address.address_reference}" if address.address_reference else ""
    return (
        f"{address.street} {address.num_street}, {address.colony}, "
        f"{address.city}, {address.state} C.P. {address.postal_code}{reference}"
    )


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
    """Formulario de envío en sus tres modos.

    - **RECEIVER**: el destinatario ya existía (pasos 5-9 del flujo). La
      referencia es la imagen del recorte y la cobertura se consulta con el
      código postal del domicilio elegido.
    - **ALTA**: la búsqueda no encontró nada (paso 7b). Llega con las
      coberturas ya consultadas y da de alta al destinatario con el OCR, sin
      volver a buscar.
    - **EDIT**: edición de un envío ya persistido, desde «Ver envíos».
    """

    def __init__(self, coverages: list[CoverageItem], ocr_form_data: dict[str, Any], 
                    parent=None, existing: ShippingDto | None = None,
                    receiver: ReceiverDto | None = None,
                    address: AddressDto | None = None,
                    contact: ContactDto | None = None,
                    crop_np=None):
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
        self._crop_np = crop_np
        self._shipment_fields: dict[str, QWidget] = {}
        self._length_labels: dict[str, QLabel] = {}
        # El destinatario fijo distingue la rama: si llega, no hay alta ni OCR.
        self._fixed_receiver = receiver
        self._selected_receiver = receiver
        self._selected_address = address
        if contact is None and receiver is not None and receiver.contacts:
            contact = receiver.contacts[0]
        self._selected_contact = contact
        self._btn_submit = None
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
        if self._is_receiver_mode:
            # Paso 6: la pantalla ya está abierta cuando se pide la cobertura
            # del domicilio; sin cobertura se cierra y se vuelve a Workspace.
            QTimer.singleShot(0, self._consult_address_coverage)
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

    @classmethod
    def for_receiver(
        cls,
        receiver: ReceiverDto,
        address: AddressDto,
        crop_np,
        parent=None,
        contact: ContactDto | None = None,
    ) -> ShipmentWindow:
        """Alta de envío con un destinatario que ya existe en el directorio."""
        return cls(
            coverages=[],
            ocr_form_data={},
            parent=parent,
            receiver=receiver,
            address=address,
            contact=contact,
            crop_np=crop_np,
        )

    @property
    def updated_shipment(self) -> ShippingDto | None:
        return self._updated_shipment

    @property
    def _is_edit(self) -> bool:
        return self._existing is not None

    @property
    def _is_receiver_mode(self) -> bool:
        return self._existing is None and self._fixed_receiver is not None

    @property
    def _is_alta_mode(self) -> bool:
        return self._existing is None and self._fixed_receiver is None

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
        if self._is_edit:
            right_column = QVBoxLayout()
            right_column.setSpacing(SPACE["md"])
            right_column.addWidget(self._build_coverage_banner())
            right_column.addWidget(self._build_coverage_card())
            right_column.addWidget(self._build_shipping_card(), 1)
            right_container = QWidget()
            right_container.setLayout(right_column)
            columns.addWidget(right_container, 1)
        else:
            columns.addWidget(self._build_reference_card(), 3)
            coverage_column = QVBoxLayout()
            coverage_column.setSpacing(SPACE["md"])
            coverage_column.addWidget(self._build_coverage_banner())
            coverage_column.addWidget(self._build_coverage_card())
            coverage_column.addStretch(1)
            coverage_container = QWidget()
            coverage_container.setLayout(coverage_column)
            columns.addWidget(coverage_container, 3)

            receiver_column = QVBoxLayout()
            receiver_column.setSpacing(SPACE["md"])
            receiver_column.addWidget(self._build_receiver_card())
            receiver_column.addWidget(self._build_package_card())
            receiver_column.addStretch(1)
            receiver_container = QWidget()
            receiver_container.setLayout(receiver_column)
            columns.addWidget(receiver_container, 6)

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
        title_column.addWidget(subtitle(self._header_hint()))
        layout.addLayout(title_column)
        layout.addStretch(1)

        if self._is_edit:
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
        if not self._is_edit:
            btn_submit.setEnabled(False)
        self._btn_submit = btn_submit
        layout.addWidget(btn_submit)
        return header

    def _header_hint(self) -> str:
        if self._is_edit:
            return "Actualiza los datos del envío y consulta cobertura si cambia la colonia."
        if self._is_receiver_mode:
            return (
                "Destinatario del directorio. Elija la colonia de cobertura y "
                "complete el paquete comparando con el recorte."
            )
        return "Dé de alta al destinatario con los datos del OCR y complete el paquete."

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
        if not self._coverages and self._is_receiver_mode:
            cp = self._selected_address.postal_code if self._selected_address else ""
            return f"Consultando cobertura para el código postal {cp}…"
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

        self._colony_combo = _NoWheelComboBox()
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

        fields = (
            ("postal_code", "Código Postal"),
            ("city", "Ciudad"),
            ("state", "Estado"),
            ("coverage_type", "Tipo de cobertura"),
        )
        # En alta la columna es estrecha: los cuatro datos van en fila propia
        # para que «CIUDAD DE MEXICO» no quede recortado.
        if self._is_edit:
            grid = QGridLayout()
            grid.setHorizontalSpacing(SPACE["md"])
            grid.setVerticalSpacing(SPACE["sm"])
            for column, (key, label) in enumerate(fields):
                self._coverage_fields[key] = self._readonly_line()
                grid.addWidget(
                    labeled_field(label, self._coverage_fields[key], mono=key == "postal_code"),
                    column // 2,
                    column % 2,
                )
            card.body.addLayout(grid)
        else:
            for key, label in fields:
                self._coverage_fields[key] = self._readonly_line()
                card.body.addWidget(
                    labeled_field(label, self._coverage_fields[key], mono=key == "postal_code")
                )
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

    def _build_receiver_card(self) -> Card:
        """Ficha fija (rama con destinatario) o alta precargada (rama sin él)."""
        if self._is_receiver_mode:
            return self._build_receiver_summary_card()
        return self._build_receiver_alta_card()

    def _build_receiver_summary_card(self) -> Card:
        """Destinatario y domicilio elegidos en Workspace; aquí no se cambian."""
        card = Card("Destinatario", "person")
        receiver = self._fixed_receiver
        address = self._selected_address

        name = QLabel(receiver_display_name(receiver))
        name.setProperty("role", "cardTitle")
        name.setWordWrap(True)
        card.body.addWidget(name)

        position = receiver_position_line(receiver)
        card.body.addWidget(subtitle(position or receiver.type_entity))

        contact = self._selected_contact
        phone = contact_display_line(contact) if contact is not None else ""
        bits = [bit for bit in (phone,) if bit]
        card.body.addWidget(subtitle(" · ".join(bits) if bits else "Sin teléfono"))

        card.body.addWidget(divider(soft=True))
        card.body.addWidget(section_label("Domicilio elegido"))
        if address is not None:
            card.body.addWidget(subtitle(_address_summary(address)))
        card.body.addWidget(
            subtitle(
                "La colonia, el código postal, la ciudad y el estado del envío "
                "salen de la cobertura, no de este domicilio."
            )
        )
        card.body.addStretch(1)
        return card

    def _build_receiver_alta_card(self) -> Card:
        """Paso 8b: alta precargada con el OCR. Esta pantalla ya no busca."""
        card = Card("Alta de destinatario", "person")
        self._alta_intro = subtitle(
            "La búsqueda no encontró al destinatario, así que se da de alta "
            "con los datos del OCR y su domicilio en la misma petición."
        )
        card.body.addWidget(self._alta_intro)

        self._alta_summary = subtitle("Todavía no se ha dado de alta al destinatario.")
        card.body.addWidget(self._alta_summary)

        self._created_box = QWidget()
        created = QVBoxLayout(self._created_box)
        created.setContentsMargins(0, 0, 0, 0)
        created.setSpacing(SPACE["xs"])
        self._created_name = QLabel("")
        self._created_name.setObjectName("createdReceiverName")
        self._created_name.setProperty("role", "cardTitle")
        self._created_name.setWordWrap(True)
        self._created_position = subtitle("")
        self._created_position.setObjectName("createdReceiverPosition")
        self._created_phone = subtitle("")
        self._created_phone.setObjectName("createdReceiverPhone")
        self._created_email = subtitle("")
        self._created_email.setObjectName("createdReceiverEmail")
        self._created_address = subtitle("")
        self._created_address.setObjectName("createdReceiverAddress")
        created.addWidget(self._created_name)
        created.addWidget(self._created_position)
        created.addWidget(self._created_phone)
        created.addWidget(self._created_email)
        created.addWidget(divider(soft=True))
        created.addWidget(section_label("Domicilio elegido"))
        created.addWidget(self._created_address)
        created.addWidget(
            subtitle(
                "La colonia, el código postal, la ciudad y el estado del envío "
                "salen de la cobertura, no de este domicilio."
            )
        )
        self._created_box.setVisible(False)
        card.body.addWidget(self._created_box)

        self._btn_alta = text_button("Dar de alta destinatario", variant="primary", icon="add")
        self._btn_alta.setObjectName("receiverCreateButton")
        self._btn_alta.setMinimumHeight(38)
        self._btn_alta.clicked.connect(self._on_alta_button)
        self._alta_card = card
        card.body.addWidget(self._btn_alta)
        card.body.addStretch(1)
        return card

    def _on_alta_button(self) -> None:
        if self._selected_receiver is None:
            self._open_receiver_alta()
            return
        self._open_receiver_edit()

    def _open_receiver_alta(self) -> None:
        from app.views.receiver_dialog import ReceiverDialog

        dialog = ReceiverDialog(self._ocr_form_data, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted or dialog.created_receiver is None:
            return
        receiver = dialog.created_receiver
        address = receiver.addresses[0] if receiver.addresses else None
        if address is None:
            QMessageBox.warning(
                self,
                "Sin domicilio",
                "El destinatario se creó sin domicilio, así que no se puede armar "
                "el envío. Regístrele uno desde el Workspace.",
            )
            return
        self._remember_created(receiver, address)
        self._refresh_coverage_from_address(address)

    def _open_receiver_edit(self) -> None:
        from app.views.receiver_dialog import ReceiverDialog

        if self._selected_receiver is None:
            return
        previous_cp = self._selected_address.postal_code if self._selected_address else ""
        dialog = ReceiverDialog.for_edit(
            self._selected_receiver,
            address=self._selected_address,
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted or dialog.created_receiver is None:
            return
        receiver = dialog.created_receiver
        address = self._address_after_edit(receiver, dialog.preferred_address_id)
        if address is None:
            QMessageBox.warning(
                self,
                "Sin domicilio",
                "El destinatario quedó sin domicilio, así que no se puede armar el envío.",
            )
            return
        self._remember_created(receiver, address, dialog.preferred_contact_id)
        if address.postal_code != previous_cp:
            self._refresh_coverage_from_address(address)

    def _address_after_edit(
        self, receiver: ReceiverDto, preferred_address_id: int | None
    ) -> AddressDto | None:
        if preferred_address_id is not None:
            match = next(
                (item for item in receiver.addresses if item.id == preferred_address_id),
                None,
            )
            if match is not None:
                return match
        return receiver.addresses[0] if receiver.addresses else None

    def _remember_created(
        self,
        receiver: ReceiverDto,
        address: AddressDto,
        contact_id: int | None = None,
    ) -> None:
        self._on_receiver_selected(receiver, address)
        if contact_id is not None:
            match = next((item for item in receiver.contacts if item.id == contact_id), None)
            if match is not None:
                self._selected_contact = match
        self._present_created_receiver(receiver, address)

    def _present_created_receiver(self, receiver: ReceiverDto, address: AddressDto) -> None:
        """Muestra la ficha del alta y deja el botón para corregir ese destinatario."""
        self._alta_intro.setVisible(False)
        self._alta_summary.setVisible(False)
        self._created_box.setVisible(True)
        self._alta_card._title_label.setText("Destinatario")
        self._created_name.setText(receiver_display_name(receiver))
        self._created_position.setText(receiver_position_line(receiver) or receiver.type_entity)
        contact = self._selected_contact
        phone = contact_display_line(contact) if contact is not None else ""
        self._created_phone.setText(phone or "Sin teléfono")
        email = (receiver.email or "").strip()
        self._created_email.setText(email or "Sin correo")
        email_field = self._shipment_fields.get("email")
        if email_field is not None and email:
            self._set_field_value(email_field, email)
        self._created_address.setText(_address_summary(address))
        self._btn_alta.setText("Editar destinatario")
        self._btn_alta.setIcon(qicon("edit_document", 18, COLOR["on_primary_container"], gap=6))
        self._btn_alta.setIconSize(QSize(24, 18))

    def _build_package_card(self) -> Card:
        """RFC y paquete. El destinatario y la calle salen del directorio."""
        card = Card("Datos del paquete", "inventory_2")
        card.body.addWidget(
            self._section(
                "Paquete",
                "inventory_2",
                [
                    [("RFC", "rfc", True, "text")],
                    [("Email", "email", True, "text")],
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

    def _build_reference_card(self) -> Card:
        """Columna izquierda: el recorte (rama con destinatario) o el OCR."""
        if self._is_receiver_mode:
            return self._build_crop_card()
        return self._build_ocr_reference_card()

    def _build_crop_card(self) -> Card:
        """Paso 5: la referencia de esta pantalla es la imagen del recorte."""
        card = Card("Recorte del sobre", "image")
        card.body.addWidget(
            subtitle(
                "Referencia de la foto: coteje contra el sobre la colonia de "
                "cobertura y los datos del paquete. No se envía al backend."
            )
        )
        card.body.addWidget(divider(soft=True))

        source = np_to_qpixmap(self._crop_np) if self._crop_np is not None else QPixmap()
        self._crop_label = _CropPreview(source)
        self._crop_label.setObjectName("shipmentCropPreview")
        if source.isNull():
            self._crop_label.setText("Sin recorte disponible")
        card.body.addWidget(self._crop_label, 1)
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
            ("numero_volante", "Número de volante"),
        ):
            line = self._readonly_line()
            self._ocr_reference_fields[key] = line
            card.body.addWidget(
                labeled_field(
                    label,
                    line,
                    mono=key in ("codigo_postal", "contacto", "numero_volante"),
                )
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
            field_widget: QWidget = _NoWheelSpinBox()
            field_widget.setRange(1, 63 if key == "package_code" else 999999)
            field_widget.setSingleStep(1)
            field_widget.setEnabled(editable)
            field_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        elif widget_type == "double":
            field_widget = _NoWheelDoubleSpinBox()
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
            if key == "email":
                field_widget.setObjectName("shipmentEmailField")
                if self._existing is None:
                    field_widget.setText(DEFAULT_SHIPMENT_EMAIL)
        self._shipment_fields[key] = field_widget
        display = field_widget
        if key in _COUNTED_KEYS and isinstance(field_widget, QLineEdit):
            display = self._with_char_count(key, field_widget)
        return labeled_field(label, display, mono=key in _MONO_KEYS)

    def _with_char_count(self, key: str, field: QLineEdit) -> QWidget:
        """Número pequeño a la derecha del recuadro: largo del texto, espacios incluidos."""
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACE["xs"])

        count = QLabel("0")
        count.setObjectName(f"shipmentFieldLength_{key}")
        count.setProperty("role", "fieldLength")
        count.setFont(mono_font(FONT_SIZE["label_sm"]))
        count.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        count.setFixedWidth(count.fontMetrics().horizontalAdvance("888"))
        count.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        def _refresh(_text: str = "") -> None:
            count.setText(str(len(field.text())))

        field.textChanged.connect(_refresh)
        _refresh()
        self._length_labels[key] = count
        layout.addWidget(field, 1)
        layout.addWidget(count, 0, Qt.AlignmentFlag.AlignVCenter)
        return row

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

    def _load_coverages(self, preferred_colony: str | None = None):
        """Llena el combo y aplica la colonia del domicilio, o la primera."""
        self._colony_combo.blockSignals(True)
        self._colony_combo.clear()
        for item in self._coverages:
            self._colony_combo.addItem(item.colony, item)
        index = preferred_coverage_index(self._coverages, preferred_colony or "")
        if self._colony_combo.count() > 0:
            self._colony_combo.setCurrentIndex(index)
        self._colony_combo.blockSignals(False)
        if self._colony_combo.count() > 0:
            self._apply_selected_coverage()
        # El combo nace con el índice 0, así que fijarlo no emite señal: hay que
        # revisar a mano si ya se puede enviar.
        self._sync_submit()

    def _refresh_coverage_from_address(self, address: AddressDto) -> None:
        """Tras el alta, la cobertura usa el domicilio devuelto por el destinatario."""
        postal_code = address.postal_code
        try:
            coverages = get_coverages_for_postal_code(postal_code)
        except PaquetexpressCoverageNotFoundError as exc:
            self._coverages = []
            self._load_coverages()
            self._banner.set_title("Sin cobertura")
            self._banner.set_message(
                f"El código postal {postal_code} del domicilio creado no tiene "
                "cobertura Paquetexpress."
            )
            QMessageBox.warning(
                self,
                "Sin cobertura",
                (
                    f"El destinatario quedó creado, pero el código postal "
                    f"{postal_code} de su domicilio no tiene cobertura, así que "
                    f"no se puede crear el envío.\n\n{exc}"
                ),
            )
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

        self._coverages = coverages
        self._load_coverages(address.colony)
        self._banner.set_title("Cobertura confirmada")
        self._banner.set_message(self._coverage_banner_message())

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

    def _consult_address_coverage(self):
        """Paso 6: cobertura del código postal del domicilio elegido.

        Un 404 aquí no crea envío ni deja registro OCR: se cierra la pantalla y
        el operador vuelve a Workspace.
        """
        if self._selected_address is None:
            self.reject()
            return
        postal_code = self._selected_address.postal_code
        try:
            coverages = get_coverages_for_postal_code(postal_code)
        except PaquetexpressCoverageNotFoundError as exc:
            QMessageBox.warning(
                self,
                "Sin cobertura",
                (
                    f"El código postal {postal_code} del domicilio elegido no "
                    "tiene cobertura Paquetexpress, así que no se crea el "
                    f"envío.\n\n{exc}"
                ),
            )
            self.reject()
            return
        except PaquetexpressSessionExpiredError as exc:
            prompt_relogin_after_session_expired(
                self, f"No se pudo consultar cobertura: {exc}"
            )
            self.reject()
            return
        except PaquetexpressServiceError as exc:
            QMessageBox.critical(
                self, "Error", f"No se pudo consultar cobertura: {exc}"
            )
            self.reject()
            return

        self._coverages = coverages
        self._load_coverages()
        self._banner.set_message(self._coverage_banner_message())

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
        self._sync_submit()

    def _on_receiver_selected(self, receiver, address) -> None:
        self._selected_receiver = receiver
        self._selected_address = address
        self._selected_contact = receiver.contacts[0] if receiver.contacts else None
        self._write_receiver_name()
        self._sync_submit()

    def _sync_submit(self) -> None:
        if self._is_edit or self._btn_submit is None:
            return
        ready = (
            self._selected_receiver is not None
            and self._selected_address is not None
            and self._selected_coverage() is not None
        )
        self._btn_submit.setEnabled(ready)

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
            self._write_receiver_name()

    # --- Envío ---------------------------------------------------------

    def _write_receiver_name(self) -> None:
        """Deja en el formulario el mismo texto que se envía en ``name_receiver``."""
        if self._selected_receiver is None:
            return
        widget = self._shipment_fields.get("name_receiver")
        if widget is None:
            return
        self._set_field_value(widget, shipment_receiver_name(self._selected_receiver))

    def chosen_for_record(self):
        """Destinatario, domicilio, cobertura y contacto usados al crear el envío."""
        coverage = self._selected_coverage()
        if (
            self._selected_receiver is None
            or self._selected_address is None
            or coverage is None
        ):
            return None
        return (
            self._selected_receiver,
            self._selected_address,
            coverage,
            self._selected_contact,
        )

    def _payload_from_receiver(self) -> dict[str, Any]:
        """Mezcla destinatario, domicilio elegido, cobertura y datos del paquete."""
        if self._selected_receiver is None or self._selected_address is None:
            return {}
        selected = self._selected_coverage()
        if selected is None:
            return {}
        package = {
            key: self._get_field_value(widget)
            for key, widget in self._shipment_fields.items()
        }
        return build_shipment_payload_from_receiver(
            self._selected_receiver,
            self._selected_address,
            selected,
            package,
            contact=self._selected_contact,
        )

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
        if not self._is_edit and (
            self._selected_receiver is None or self._selected_address is None
        ):
            QMessageBox.warning(
                self,
                "Falta destinatario",
                "Dé de alta al destinatario con su domicilio antes de crear el envío."
                if self._is_alta_mode
                else "Seleccione un destinatario y un domicilio.",
            )
            return
        if self._is_edit:
            payload = self._shipment_payload_from_form()
        else:
            payload = self._payload_from_receiver()
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
                f"• {error['campo']}: {error['error']}." for error in exc.errors
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
            if key in campos_normalizados:
                self._set_field_value(widget, campos_normalizados.get(key, ""))
            elif key == "email":
                self._set_field_value(widget, normalize_email(str(payload.get("email") or "")))