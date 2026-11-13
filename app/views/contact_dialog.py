"""Diálogo corto para registrar o editar un teléfono de un destinatario."""

from __future__ import annotations

from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QVBoxLayout

from app.components.theme import SPACE
from app.components.widgets import labeled_field, text_button
from app.models.receiver import ContactDto
from app.services import contacts_service
from app.states.workers.callable_worker import run_worker
from app.views.session_relogin import prompt_relogin_after_session_expired


class ContactDialog(QDialog):
    """Alta o edición de contacto. Un 409 avisa y deja corregir el teléfono."""

    def __init__(self, receiver_id: int, parent=None, contact: ContactDto | None = None):
        super().__init__(parent)
        self.setObjectName("ContactDialog")
        self._receiver_id = receiver_id
        self._contact = contact
        self._busy = False
        self.created_contact: ContactDto | None = None
        editing = contact is not None
        self.setWindowTitle("Editar contacto" if editing else "Agregar contacto")
        self.resize(420, 220)

        root = QVBoxLayout(self)
        root.setContentsMargins(SPACE["lg"], SPACE["md"], SPACE["lg"], SPACE["md"])
        root.setSpacing(SPACE["md"])
        title = QLabel("Editar teléfono" if editing else "Nuevo teléfono")
        title.setProperty("role", "headline")
        root.addWidget(title)

        self._phone = QLineEdit()
        self._phone.setObjectName("contactPhoneInput")
        self._phone.setMaxLength(10)
        self._phone.setPlaceholderText("10 dígitos")
        self._ext = QLineEdit()
        self._ext.setMaxLength(5)
        self._ext.setPlaceholderText("Ext.")
        if contact is not None:
            self._phone.setText(contact.phone or "")
            self._ext.setText(contact.ext or "")
        row = QHBoxLayout()
        row.setSpacing(SPACE["sm"])
        row.addWidget(labeled_field("Teléfono", self._phone), 2)
        row.addWidget(labeled_field("Extensión", self._ext), 1)
        root.addLayout(row)

        actions = QHBoxLayout()
        actions.addStretch(1)
        cancel = text_button("Cancelar", variant="ghost", icon="close")
        cancel.clicked.connect(self.reject)
        self._save = text_button("Guardar contacto", variant="primary", icon="save")
        self._save.setObjectName("saveContactButton")
        self._save.clicked.connect(self._on_save)
        actions.addWidget(cancel)
        actions.addWidget(self._save)
        root.addLayout(actions)

    def _on_save(self) -> None:
        if self._busy:
            return
        self._busy = True
        self._save.setEnabled(False)
        payload = {"phone": self._phone.text().strip(), "ext": self._ext.text().strip()}
        if self._contact is not None:
            contact = self._contact
            run_worker(
                self,
                lambda: contacts_service.update_contact(contact.id, payload, contact),
                self._on_created,
                self._on_failed,
            )
            return
        run_worker(
            self,
            lambda: contacts_service.create_contact(self._receiver_id, payload),
            self._on_created,
            self._on_failed,
        )

    def _on_created(self, contact: ContactDto) -> None:
        self._busy = False
        self._save.setEnabled(True)
        self.created_contact = contact
        self.accept()

    def _on_failed(self, exc: Exception) -> None:
        self._busy = False
        self._save.setEnabled(True)
        if isinstance(exc, contacts_service.ContactDuplicateError):
            QMessageBox.information(self, "Contacto existente", str(exc))
            return
        if isinstance(exc, contacts_service.ContactSessionExpiredError):
            prompt_relogin_after_session_expired(self, str(exc))
            return
        if isinstance(exc, contacts_service.ContactValidationError):
            details = "\n".join(f"• {item['campo']}: {item['error']}." for item in exc.errors)
            QMessageBox.critical(self, "Errores de validación", details or str(exc))
            return
        QMessageBox.critical(self, "Error", str(exc))
