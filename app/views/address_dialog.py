"""Diálogo para registrar un domicilio en un destinatario existente."""

from __future__ import annotations

from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QMessageBox, QVBoxLayout

from app.components.address_form import AddressFormWidget
from app.components.theme import SPACE
from app.components.widgets import text_button
from app.models.receiver import AddressDto
from app.services import addresses_service
from app.states.workers.callable_worker import run_worker
from app.views.session_relogin import prompt_relogin_after_session_expired


class AddressDialog(QDialog):
    """Alta o edición de domicilio. Si ya existe uno equivalente, devuelve su id."""

    def __init__(self, receiver_id: int, parent=None, address: AddressDto | None = None):
        super().__init__(parent)
        self.setObjectName("AddressDialog")
        self._receiver_id = receiver_id
        self._address = address
        self._busy = False
        self.created_address: AddressDto | None = None
        self.duplicate_address_id: int | None = None
        editing = address is not None
        self.setWindowTitle("Editar domicilio" if editing else "Registrar domicilio")
        self.resize(640, 560)

        root = QVBoxLayout(self)
        root.setContentsMargins(SPACE["lg"], SPACE["md"], SPACE["lg"], SPACE["md"])
        root.setSpacing(SPACE["md"])
        title = QLabel("Editar domicilio" if editing else "Nuevo domicilio")
        title.setProperty("role", "headline")
        root.addWidget(title)
        self._form = AddressFormWidget()
        if address is not None:
            self._form.set_from_address(address)
        root.addWidget(self._form, 1)

        actions = QHBoxLayout()
        actions.addStretch(1)
        cancel = text_button("Cancelar", variant="ghost", icon="close")
        cancel.clicked.connect(self.reject)
        self._save = text_button("Guardar domicilio", variant="primary", icon="save")
        self._save.clicked.connect(self._on_save)
        actions.addWidget(cancel)
        actions.addWidget(self._save)
        root.addLayout(actions)

    def _on_save(self) -> None:
        if self._busy:
            return
        self._busy = True
        self._save.setEnabled(False)
        payload = self._form.get_payload()
        if self._address is not None:
            run_worker(
                self,
                lambda: addresses_service.update_address(
                    self._address.id, payload, self._address
                ),
                self._on_created,
                self._on_failed,
            )
            return
        run_worker(
            self,
            lambda: addresses_service.create_address(self._receiver_id, payload),
            self._on_created,
            self._on_failed,
        )

    def _on_created(self, address: AddressDto) -> None:
        self._busy = False
        self._save.setEnabled(True)
        self.created_address = address
        self.accept()

    def _on_failed(self, exc: Exception) -> None:
        self._busy = False
        self._save.setEnabled(True)
        if isinstance(exc, addresses_service.AddressDuplicateError):
            self.duplicate_address_id = exc.address_id
            QMessageBox.information(
                self,
                "Domicilio existente",
                f"{exc}\n\nSe usará el domicilio {exc.address_id}.",
            )
            self.accept()
            return
        if isinstance(exc, addresses_service.AddressSessionExpiredError):
            prompt_relogin_after_session_expired(self, str(exc))
            return
        if isinstance(exc, addresses_service.AddressValidationError):
            details = "\n".join(f"• {item['campo']}: {item['error']}." for item in exc.errors)
            QMessageBox.critical(self, "Errores de validación", details or str(exc))
            return
        QMessageBox.critical(self, "Error", str(exc))
