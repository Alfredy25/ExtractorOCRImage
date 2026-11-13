"""Diálogo para crear un destinatario y dejarlo seleccionado en el envío."""

from __future__ import annotations

import re
from typing import Any

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.components.address_form import AddressFormWidget
from app.components.autocomplete_combo import AutocompleteComboBox
from app.components.theme import SPACE
from app.components.widgets import (
    Card,
    labeled_field,
    set_property,
    subtitle,
    text_button,
)
from app.models.receiver import (
    AddressDto,
    ReceiverDto,
    contact_display_line,
    persona_shipment_name,
)
from app.services import catalogs_service, receivers_service
from app.utils.image_io import np_to_qpixmap
from app.states.workers.callable_worker import run_worker
from app.utils.normalizers import (
    clean_base_text,
    normalize_email,
    normalize_full_name,
    normalize_job_role,
    normalize_organization,
    normalize_phone,
    normalize_title,
)
from app.views.session_relogin import prompt_relogin_after_session_expired

_OCR_FIELDS = (
    ("nombre_titulo", "Nombre OCR"),
    ("cargo_dependencia", "Cargo OCR"),
    ("estado", "Estado OCR"),
    ("municipio_alcaldia", "Ciudad OCR"),
    ("colonia", "Colonia OCR"),
    ("codigo_postal", "Código Postal OCR"),
    ("direccion", "Dirección OCR"),
    ("contacto", "Contacto OCR"),
    ("indicaciones", "Indicaciones OCR"),
)

_TITLE_FIELDS = (
    ("abbreviation", "Abreviatura", "upper", 60),
    ("meaning", "Significado", "text", 150),
)
_ROLE_FIELDS = (
    ("abbreviation", "Abreviatura", "upper", 60),
    ("meaning", "Significado", "text", 150),
)
_ORG_FIELDS = (
    ("name", "Nombre", "text", 180),
    ("state", "Estado", "state", 0),
)
_VOLANTE_FIELDS = (("name", "Nombre del volante", "upper", 35),)


def _digits(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    if len(digits) > 10:
        return digits[-10:]
    return digits


class _CropPreview(QLabel):
    """Imagen del recorte ajustada al ancho de su columna, sin deformarla."""

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


class ReceiverDialog(QDialog):
    """Alta de PERSONA, GOBIERNO o PRIVADA, o edición de identidad."""

    def __init__(
        self,
        ocr_form_data: dict[str, Any] | None = None,
        parent=None,
        *,
        receiver: ReceiverDto | None = None,
        crop_np=None,
        address: AddressDto | None = None,
    ):
        super().__init__(parent)
        self.setObjectName("ReceiverDialog")
        self._receiver = receiver
        self._crop_np = crop_np
        self._is_edit = receiver is not None
        if address is not None:
            self._current_address_id = address.id
        elif receiver is not None and receiver.addresses:
            self._current_address_id = receiver.addresses[0].id
        else:
            self._current_address_id = None
        self.preferred_address_id = self._current_address_id
        if receiver is not None and receiver.contacts:
            self.preferred_contact_id = receiver.contacts[0].id
        else:
            self.preferred_contact_id = None
        self.setWindowTitle("Editar destinatario" if self._is_edit else "Crear destinatario")
        self.resize(1180, 800)
        self.setMinimumSize(960, 640)
        self.setWindowFlag(Qt.WindowType.WindowMinMaxButtonsHint, True)
        self._ocr = ocr_form_data or {}
        self._campos = self._ocr.get("campos") or {}
        self._type = "PERSONA"
        self._busy = False
        self.created_receiver: ReceiverDto | None = None
        self._setup_ui()
        if self._is_edit:
            self._apply_receiver()
        else:
            self._apply_ocr()
            self._set_type("PERSONA")

    @classmethod
    def for_edit(
        cls,
        receiver: ReceiverDto,
        crop_np=None,
        address: AddressDto | None = None,
        parent=None,
    ) -> ReceiverDialog:
        return cls(parent=parent, receiver=receiver, crop_np=crop_np, address=address)

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(SPACE["lg"], SPACE["md"], SPACE["lg"], SPACE["md"])
        root.setSpacing(SPACE["md"])

        header = QVBoxLayout()
        title = QLabel("Editar destinatario" if self._is_edit else "Crear destinatario")
        title.setProperty("role", "headline")
        header.addWidget(title)
        header.addWidget(
            subtitle(
                "Corrija la identidad. Domicilio y contacto se agregan o editan con sus botones."
                if self._is_edit
                else "Contraste los datos del sobre y deje listo el destinatario para este envío."
            )
        )
        root.addLayout(header)

        body = QWidget()
        columns = QHBoxLayout(body)
        columns.setContentsMargins(0, 0, 0, 0)
        columns.setSpacing(SPACE["md"])
        columns.addWidget(self._build_crop_card() if self._is_edit else self._build_ocr_card(), 4)

        form = QWidget()
        form_layout = QVBoxLayout(form)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(SPACE["md"])
        normalize_row = QHBoxLayout()
        normalize_row.setContentsMargins(0, 0, 0, 0)
        normalize = text_button("Normalizar campos", variant="ghost", icon="refresh")
        normalize.clicked.connect(self._normalize_fields)
        normalize_row.addWidget(normalize)
        normalize_row.addStretch(1)
        form_layout.addLayout(normalize_row)
        form_layout.addWidget(self._build_identity_card())
        form_layout.addWidget(self._build_contact_card())
        form_layout.addWidget(self._build_address_card())
        form_layout.addWidget(self._build_volante_card())
        form_layout.addStretch(1)
        columns.addWidget(form, 8)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(body)
        # Ignored: si no, el alto del formulario empuja los botones encima del domicilio.
        scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Ignored)
        root.addWidget(scroll, 1)

        actions = QHBoxLayout()
        refill = text_button("Rellenar con datos OCR", variant="ghost", icon="refresh")
        refill.clicked.connect(self._apply_ocr)
        refill.setVisible(not self._is_edit)
        actions.addWidget(refill)
        actions.addStretch(1)
        cancel = text_button("Volver", variant="ghost", icon="close")
        cancel.clicked.connect(self.reject)
        save_label = "Guardar cambios" if self._is_edit else "Guardar y usar en envío"
        self._save_button = text_button(save_label, variant="primary", icon="save")
        self._save_button.setObjectName("receiverSaveButton")
        self._save_button.clicked.connect(self._on_save)
        actions.addWidget(cancel)
        actions.addWidget(self._save_button)
        root.addLayout(actions)

    def _build_crop_card(self) -> Card:
        card = Card("Recorte del sobre", "document_scanner")
        if self._crop_np is None:
            empty = QLabel("Sin recorte disponible")
            empty.setObjectName("cropUnavailableLabel")
            empty.setWordWrap(True)
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setMinimumHeight(260)
            card.body.addWidget(empty)
            return card
        preview = _CropPreview(np_to_qpixmap(self._crop_np))
        preview.setObjectName("receiverCropPreview")
        card.body.addWidget(preview, 1)
        return card

    def _build_ocr_card(self) -> Card:
        card = Card("Referencia OCR", "document_scanner")
        card.body.addWidget(subtitle("Solo lectura. No se envían tal cual: sirven para copiar."))
        for key, label in _OCR_FIELDS:
            line = QLineEdit(str(self._campos.get(key) or "").strip())
            line.setReadOnly(True)
            line.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            line.setCursor(Qt.CursorShape.IBeamCursor)
            card.body.addWidget(labeled_field(label, line, mono=key in {"codigo_postal", "contacto"}))
        return card

    def _build_identity_card(self) -> Card:
        card = Card("Identidad", "badge")
        types = QHBoxLayout()
        self._type_buttons: dict[str, QWidget] = {}
        for key, label in (("PERSONA", "Persona"), ("GOBIERNO", "Gobierno"), ("PRIVADA", "Privada")):
            button = text_button(label, variant="ghost")
            button.clicked.connect(lambda _checked=False, kind=key: self._set_type(kind))
            self._type_buttons[key] = button
            types.addWidget(button)
        card.body.addLayout(types)
        self._type_hint = subtitle("Persona: título y nombre obligatorios.")
        card.body.addWidget(self._type_hint)

        self._persona = QWidget()
        persona_layout = QVBoxLayout(self._persona)
        persona_layout.setContentsMargins(0, 0, 0, 0)
        persona_layout.setSpacing(SPACE["sm"])
        self._title = AutocompleteComboBox(
            catalogs_service.search_titles,
            lambda item: f"{item.abbreviation} — {item.meaning}",
            create_fn=lambda data: catalogs_service.create_title(data["abbreviation"], data["meaning"]),
            create_title="Nuevo título",
            create_fields=list(_TITLE_FIELDS),
            field_normalizers={"abbreviation": normalize_title},
            placeholder="Buscar título (LIC., DR.)",
        )
        self._title.selection_changed.connect(self._refresh_preview)
        persona_layout.addWidget(labeled_field("Título", self._title))
        persona_layout.addWidget(self._title.status_widget())
        self._name = QLineEdit()
        self._name.setMaxLength(70)
        self._name.setPlaceholderText("NOMBRE Y APELLIDOS")
        self._name.textEdited.connect(self._upper_name)
        persona_layout.addWidget(labeled_field("Nombre completo", self._name))
        card.body.addWidget(self._persona)

        self._org = AutocompleteComboBox(
            catalogs_service.search_organizations,
            lambda item: f"{item.name} · {item.state}",
            create_fn=lambda data: catalogs_service.create_organization(data["name"], data["state"]),
            create_title="Nueva organización",
            create_fields=list(_ORG_FIELDS),
            field_normalizers={"name": normalize_organization},
            placeholder="Buscar organización",
        )
        self._org.selection_changed.connect(self._refresh_preview)
        card.body.addWidget(labeled_field("Organización", self._org))
        card.body.addWidget(self._org.status_widget())

        self._role = AutocompleteComboBox(
            catalogs_service.search_job_roles,
            lambda item: f"{item.abbreviation} — {item.meaning}",
            create_fn=lambda data: catalogs_service.create_job_role(data["abbreviation"], data["meaning"]),
            create_title="Nuevo cargo",
            create_fields=list(_ROLE_FIELDS),
            field_normalizers={
                "abbreviation": normalize_job_role,
                "meaning": clean_base_text,
            },
            normalize_together=True,
            placeholder="Buscar cargo (opcional)",
        )
        self._role.selection_changed.connect(self._refresh_preview)
        card.body.addWidget(labeled_field("Cargo", self._role))
        card.body.addWidget(self._role.status_widget())

        self._preview = subtitle("")
        card.body.addWidget(self._preview)
        return card

    def _build_contact_card(self) -> Card:
        card = Card("Contacto", "mail")
        self._email = QLineEdit()
        self._email.setPlaceholderText("correo@dependencia.gob.mx")
        self._email.setMaxLength(80)
        card.body.addWidget(labeled_field("Correo", self._email))
        self._phone = QLineEdit()
        self._phone.setMaxLength(10)
        self._phone.setPlaceholderText("10 dígitos")
        self._ext = QLineEdit()
        self._ext.setMaxLength(5)
        self._ext.setPlaceholderText("Ext.")
        self._phone_create_row = QWidget()
        row = QHBoxLayout(self._phone_create_row)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(SPACE["sm"])
        row.addWidget(labeled_field("Teléfono", self._phone), 2)
        row.addWidget(labeled_field("Extensión", self._ext), 1)
        self._phone_create_row.setVisible(not self._is_edit)
        card.body.addWidget(self._phone_create_row)

        self._contacts_host = QWidget()
        self._contacts_host.setVisible(self._is_edit)
        contacts_layout = QVBoxLayout(self._contacts_host)
        contacts_layout.setContentsMargins(0, 0, 0, 0)
        contacts_layout.setSpacing(SPACE["xs"])
        contacts_layout.addWidget(subtitle("Teléfonos registrados"))
        self._contacts_layout = QVBoxLayout()
        self._contacts_layout.setSpacing(SPACE["xs"])
        contacts_layout.addLayout(self._contacts_layout)
        card.body.addWidget(self._contacts_host)

        self._btn_add_contact = text_button("Agregar contacto", variant="ghost", icon="add")
        self._btn_add_contact.setObjectName("addContactButton")
        self._btn_add_contact.clicked.connect(self._add_contact)
        self._btn_add_contact.setVisible(self._is_edit)
        card.body.addWidget(self._btn_add_contact, 0, Qt.AlignmentFlag.AlignLeft)
        return card

    def _build_address_card(self) -> Card:
        card = Card("Domicilio" if self._is_edit else "Domicilio inicial", "place")
        if self._is_edit:
            buttons = QHBoxLayout()
            buttons.setContentsMargins(0, 0, 0, 0)
            buttons.setSpacing(SPACE["sm"])
            self._btn_add_address = text_button("Agregar domicilio", variant="ghost", icon="add")
            self._btn_add_address.setObjectName("addAddressButton")
            self._btn_add_address.clicked.connect(self._add_address)
            self._btn_edit_address = text_button(
                "Editar domicilio", variant="ghost", icon="edit_document"
            )
            self._btn_edit_address.setObjectName("editAddressButton")
            self._btn_edit_address.clicked.connect(self._edit_address)
            buttons.addWidget(self._btn_add_address)
            buttons.addWidget(self._btn_edit_address)
            buttons.addStretch(1)
            card.body.addLayout(buttons)
        self._address = AddressFormWidget()
        card.body.addWidget(self._address)
        return card

    def _build_volante_card(self) -> Card:
        card = Card("Volante", "receipt_long")
        card.body.addWidget(subtitle("Opcional. El nombre debe tener entre 18 y 35 caracteres."))
        self._volante = AutocompleteComboBox(
            catalogs_service.search_volantes,
            lambda item: item.name,
            create_fn=lambda data: catalogs_service.create_volante(data["name"]),
            create_title="Nuevo volante",
            create_fields=list(_VOLANTE_FIELDS),
            placeholder="Buscar volante",
        )
        card.body.addWidget(self._volante)
        card.body.addWidget(self._volante.status_widget())
        return card

    def _set_type(self, kind: str) -> None:
        self._type = kind
        persona = kind == "PERSONA"
        self._persona.setVisible(persona)
        for key, button in self._type_buttons.items():
            set_property(button, "variant", "primary" if key == kind else "ghost")
        if persona:
            self._type_hint.setText("Persona: título y nombre obligatorios. Organización y cargo son opcionales.")
        else:
            self._type_hint.setText(
                f"{kind}: la organización es obligatoria. No se envía nombre ni título."
            )
        self._refresh_preview()

    def _normalize_fields(self) -> None:
        self._name.setText(normalize_full_name(self._name.text()))
        self._email.setText(normalize_email(self._email.text()))
        self._phone.setText(normalize_phone(self._phone.text()))
        self._ext.setText(normalize_phone(self._ext.text()))
        self._address.normalize_street_and_number()
        self._refresh_preview()

    def _upper_name(self, text: str) -> None:
        upper = text.upper()
        if upper != text:
            pos = self._name.cursorPosition()
            self._name.blockSignals(True)
            self._name.setText(upper)
            self._name.setCursorPosition(pos)
            self._name.blockSignals(False)
        self._refresh_preview()

    def _refresh_preview(self) -> None:
        org = self._org.selected()
        role = self._role.selected()
        title = self._title.selected()
        org_name = org.name if org is not None else ""
        role_name = role.meaning if role is not None else ""
        if self._type == "PERSONA":
            text = persona_shipment_name(
                title.abbreviation if title is not None else "",
                self._name.text(),
                role.abbreviation if role is not None else "",
                org_name,
            ) or "Sin datos de identidad"
        else:
            if org_name and role_name:
                text = f"{org_name} [{role_name}]"
            else:
                text = org_name or "Seleccione una organización"
        self._preview.setText(text)

    def _apply_ocr(self) -> None:
        self._name.setText(str(self._campos.get("nombre_titulo") or "").strip().upper())
        self._phone.setText(_digits(str(self._campos.get("contacto") or "")))
        self._address.set_initial_from_ocr(self._campos)
        self._refresh_preview()

    def _warn(self, message: str) -> None:
        QMessageBox.warning(self, "Faltan datos", message)

    def _on_save(self) -> None:
        if self._busy:
            return
        if not self._is_edit and self._volante.text() and self._volante.selected() is None:
            self._warn("Seleccione el volante de la lista o créelo. Si no aplica, borre el texto.")
            return
        if self._role.text() and self._role.selected() is None:
            self._warn("Seleccione el cargo de la lista o créelo. Si no aplica, borre el texto.")
            return
        if self._org.text() and self._org.selected() is None:
            self._warn("Seleccione la organización de la lista o créela.")
            return
        if self._type == "PERSONA":
            if self._title.selected() is None:
                self._warn("Seleccione un título o créelo.")
                return
        elif self._org.selected() is None:
            self._warn("Seleccione una organización o créela.")
            return
        if self._role.selected() is not None and self._org.selected() is None:
            self._warn("El cargo necesita una organización.")
            return

        self._busy = True
        self._save_button.setEnabled(False)
        payload = self._collect()
        if self._is_edit and self._receiver is not None:
            receiver = self._receiver
            run_worker(
                self,
                lambda: receivers_service.update_receiver(receiver.id, payload, receiver),
                self._on_updated,
                self._on_failed,
            )
            return
        run_worker(
            self,
            lambda: receivers_service.create_receiver(payload),
            self._on_created,
            self._on_failed,
        )

    def _collect(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "type_entity": self._type,
            "email": self._email.text().strip(),
            "address": self._address.get_payload(),
            "volante_name": "",
        }
        phone = self._phone.text().strip()
        if phone:
            data["contact"] = {"phone": phone, "ext": self._ext.text().strip()}
        volante = self._volante.selected()
        if volante is not None:
            data["volante_name"] = volante.name
        if self._type == "PERSONA":
            data["full_name"] = self._name.text().strip()
            title = self._title.selected()
            if title is not None:
                data["title"] = {
                    "abbreviation": title.abbreviation,
                    "meaning": title.meaning,
                }
        org = self._org.selected()
        role = self._role.selected()
        if org is not None:
            data["organization"] = {"name": org.name, "state": org.state}
        if role is not None:
            data["job_role"] = {
                "abbreviation": role.abbreviation,
                "meaning": role.meaning,
            }
        return data

    def _on_created(self, receiver: ReceiverDto) -> None:
        self._busy = False
        self._save_button.setEnabled(True)
        self.created_receiver = receiver
        self.accept()

    def _on_updated(self, receiver: ReceiverDto) -> None:
        self._busy = False
        self._save_button.setEnabled(True)
        self._receiver = self._merge_lists(receiver)
        self.created_receiver = self._receiver
        self.preferred_address_id = self._current_address_id
        self.accept()

    def _apply_receiver(self) -> None:
        receiver = self._receiver
        if receiver is None:
            return
        self._set_type(receiver.type_entity)
        for button in self._type_buttons.values():
            button.setEnabled(False)
        self._volante.setEnabled(False)
        if receiver.title is not None:
            self._title.set_selected(receiver.title)
        if receiver.full_name:
            self._name.setText(receiver.full_name)
        if receiver.email:
            self._email.setText(receiver.email)
        self._refresh_contacts_list()
        if receiver.position is not None:
            self._org.set_selected(receiver.position.organization)
            if receiver.position.job_role is not None:
                self._role.set_selected(receiver.position.job_role)
        if receiver.volantes:
            self._volante.set_selected(receiver.volantes[0])
        current = self._current_address()
        if current is not None:
            self._address.set_from_address(current)
        if hasattr(self, "_btn_edit_address"):
            self._btn_edit_address.setEnabled(current is not None)
        self._refresh_preview()

    def _current_address(self) -> AddressDto | None:
        if self._receiver is None:
            return None
        if self._current_address_id is not None:
            match = next(
                (item for item in self._receiver.addresses if item.id == self._current_address_id),
                None,
            )
            if match is not None:
                return match
        if self._receiver.addresses:
            return self._receiver.addresses[0]
        return None

    def _merge_lists(self, receiver: ReceiverDto) -> ReceiverDto:
        """Conserva domicilios y contactos locales si el PATCH no los trae actualizados."""
        if self._receiver is None:
            return receiver

        def _union(server, local):
            merged = {item.id: item for item in server}
            for item in local:
                merged.setdefault(item.id, item)
            return list(merged.values())

        updates: dict[str, Any] = {
            "addresses": _union(receiver.addresses, self._receiver.addresses),
            "contacts": _union(receiver.contacts, self._receiver.contacts),
        }
        if not receiver.volantes and self._receiver.volantes:
            updates["volantes"] = self._receiver.volantes
        return receiver.model_copy(update=updates)

    def _replace_address(self, address: AddressDto) -> None:
        if self._receiver is None:
            return
        addresses = [item for item in self._receiver.addresses if item.id != address.id]
        addresses.append(address)
        self._receiver = self._receiver.model_copy(update={"addresses": addresses})
        self._current_address_id = address.id
        self.preferred_address_id = address.id
        self.created_receiver = self._receiver
        self._address.set_from_address(address)
        if hasattr(self, "_btn_edit_address"):
            self._btn_edit_address.setEnabled(True)

    def _add_address(self) -> None:
        if self._receiver is None:
            return
        from app.views.address_dialog import AddressDialog

        dialog = AddressDialog(self._receiver.id, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        if dialog.created_address is not None:
            self._replace_address(dialog.created_address)
            return
        if dialog.duplicate_address_id is None:
            return
        match = next(
            (item for item in self._receiver.addresses if item.id == dialog.duplicate_address_id),
            None,
        )
        if match is not None:
            self._current_address_id = match.id
            self.preferred_address_id = match.id
            self._address.set_from_address(match)
            return
        QMessageBox.information(
            self,
            "Domicilio existente",
            "Ese domicilio ya estaba registrado. Vuelva a buscar al destinatario para verlo.",
        )

    def _edit_address(self) -> None:
        if self._receiver is None:
            return
        current = self._current_address()
        if current is None:
            QMessageBox.information(
                self,
                "Sin domicilio",
                "Este destinatario no tiene domicilio. Agregue uno primero.",
            )
            return
        from app.views.address_dialog import AddressDialog

        dialog = AddressDialog(self._receiver.id, parent=self, address=current)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        if dialog.created_address is not None:
            self._replace_address(dialog.created_address)
            return
        if dialog.duplicate_address_id is None:
            return
        match = next(
            (item for item in self._receiver.addresses if item.id == dialog.duplicate_address_id),
            None,
        )
        if match is not None:
            self._current_address_id = match.id
            self.preferred_address_id = match.id
            self._address.set_from_address(match)

    def _add_contact(self) -> None:
        if self._receiver is None:
            return
        from app.views.contact_dialog import ContactDialog

        dialog = ContactDialog(self._receiver.id, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        if dialog.created_contact is None:
            return
        created = dialog.created_contact
        existing = [item for item in self._receiver.contacts if item.id != created.id]
        contacts = [*existing, created]
        self._receiver = self._receiver.model_copy(update={"contacts": contacts})
        self.created_receiver = self._receiver
        self.preferred_contact_id = created.id
        self._refresh_contacts_list()

    def _refresh_contacts_list(self) -> None:
        while self._contacts_layout.count():
            item = self._contacts_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        contacts = self._receiver.contacts if self._receiver is not None else []
        if not contacts:
            empty = subtitle("Sin teléfonos registrados")
            empty.setObjectName("receiverContactsEmpty")
            self._contacts_layout.addWidget(empty)
            return
        for contact in contacts:
            line = subtitle(contact_display_line(contact))
            line.setObjectName("receiverContactItem")
            self._contacts_layout.addWidget(line)

    def _on_failed(self, exc: Exception) -> None:
        self._busy = False
        self._save_button.setEnabled(True)
        if isinstance(exc, receivers_service.ReceiverDuplicateError):
            if self._is_edit:
                QMessageBox.critical(
                    self,
                    "Destinatario duplicado",
                    f"Otro destinatario ya tiene esos datos (id {exc.receiver_id}).",
                )
                return
            self._offer_duplicate(exc.receiver_id)
            return
        if isinstance(exc, receivers_service.ReceiverSessionExpiredError):
            prompt_relogin_after_session_expired(self, str(exc))
            return
        if isinstance(exc, receivers_service.ReceiverValidationError):
            details = "\n".join(f"• {item['campo']}: {item['error']}." for item in exc.errors)
            QMessageBox.critical(self, "Errores de validación", details or str(exc))
            return
        QMessageBox.critical(self, "Error", str(exc))

    def _offer_duplicate(self, receiver_id: int) -> None:
        answer = QMessageBox.question(
            self,
            "Destinatario existente",
            f"Ese destinatario ya existe (id {receiver_id}). ¿Usarlo en este envío?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        term = self._duplicate_query()
        if len(term) < 3:
            QMessageBox.information(
                self,
                "Destinatario existente",
                f"El id es {receiver_id}. Búsquelo por nombre en la pantalla de envío.",
            )
            return
        self._busy = True
        self._save_button.setEnabled(False)
        run_worker(
            self,
            lambda: receivers_service.search_receivers(term, page_size=50),
            lambda page, wanted=receiver_id: self._take_duplicate(page, wanted),
            self._on_failed,
        )

    def _duplicate_query(self) -> str:
        if self._type == "PERSONA":
            raw = self._name.text()
        else:
            org = self._org.selected()
            raw = org.name if org is not None else ""
        cleaned = re.sub(r"[^0-9A-Za-zÁÉÍÓÚáéíóúÑñÜü .\-]", "", raw)
        return re.sub(r"\s+", " ", cleaned).strip()[:40]

    def _take_duplicate(self, page, receiver_id: int) -> None:
        self._busy = False
        self._save_button.setEnabled(True)
        for item in page.items:
            if item.id == receiver_id:
                self.created_receiver = item
                self.accept()
                return
        QMessageBox.information(
            self,
            "Destinatario existente",
            f"El destinatario {receiver_id} ya existe, pero no apareció en la búsqueda. "
            "Ciérrelo y búsquelo en la pantalla de envío.",
        )
