"""Diálogo para buscar o crear un volante y enlazarlo a un destinatario."""

from __future__ import annotations

from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QMessageBox, QVBoxLayout

from app.components.autocomplete_combo import AutocompleteComboBox
from app.components.theme import SPACE
from app.components.widgets import labeled_field, subtitle, text_button
from app.models.receiver import VolanteDto
from app.services import catalogs_service, receivers_service
from app.states.workers.callable_worker import run_worker
from app.views.session_relogin import prompt_relogin_after_session_expired

_VOLANTE_FIELDS = (("name", "Nombre del volante", "upper", 35),)


class VolanteDialog(QDialog):
    """Busca en el catálogo, permite crearlo y después lo asigna.

    El 409 solo sale al asignar, si ese destinatario ya tiene el volante.
    """

    def __init__(self, receiver_id: int, parent=None):
        super().__init__(parent)
        self.setObjectName("VolanteDialog")
        self.setWindowTitle("Añadir nuevo volante")
        self.resize(520, 280)
        self._receiver_id = receiver_id
        self._busy = False
        self.created_volante: VolanteDto | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(SPACE["lg"], SPACE["md"], SPACE["lg"], SPACE["md"])
        root.setSpacing(SPACE["md"])
        title = QLabel("Nuevo volante")
        title.setProperty("role", "headline")
        root.addWidget(title)
        root.addWidget(
            subtitle(
                "Escriba para buscar. Si no existe, créelo. "
                "Al añadirlo se asigna a este destinatario."
            )
        )

        self._volante = AutocompleteComboBox(
            catalogs_service.search_volantes,
            lambda item: item.name,
            create_fn=lambda data: catalogs_service.create_volante(data["name"]),
            create_title="Nuevo volante",
            create_fields=list(_VOLANTE_FIELDS),
            placeholder="Buscar volante",
        )
        root.addWidget(labeled_field("Número de volante", self._volante))
        root.addWidget(self._volante.status_widget())

        actions = QHBoxLayout()
        actions.addStretch(1)
        cancel = text_button("Cancelar", variant="ghost", icon="close")
        cancel.clicked.connect(self.reject)
        self._save = text_button("Añadir volante", variant="primary", icon="save")
        self._save.setObjectName("saveVolanteButton")
        self._save.clicked.connect(self._on_save)
        actions.addWidget(cancel)
        actions.addWidget(self._save)
        root.addLayout(actions)

    def _on_save(self) -> None:
        if self._busy:
            return
        selected = self._volante.selected()
        if selected is None:
            QMessageBox.warning(
                self,
                "Falta el volante",
                "Seleccione el volante de la lista o créelo. Si no aplica, cancele.",
            )
            return
        self._busy = True
        self._save.setEnabled(False)
        name = selected.name
        run_worker(
            self,
            lambda: receivers_service.add_volante(self._receiver_id, name),
            self._on_assigned,
            self._on_failed,
        )

    def _on_assigned(self, volante: VolanteDto) -> None:
        self._busy = False
        self._save.setEnabled(True)
        self.created_volante = volante
        self.accept()

    def _on_failed(self, exc: Exception) -> None:
        self._busy = False
        self._save.setEnabled(True)
        if isinstance(exc, receivers_service.ReceiverVolanteDuplicateError):
            QMessageBox.information(
                self,
                "Volante ya asignado",
                "Este destinatario ya tiene ese volante.",
            )
            return
        if isinstance(exc, receivers_service.ReceiverSessionExpiredError):
            prompt_relogin_after_session_expired(self, str(exc))
            return
        if isinstance(exc, receivers_service.ReceiverValidationError):
            details = "\n".join(f"• {item['campo']}: {item['error']}." for item in exc.errors)
            QMessageBox.critical(self, "Errores de validación", details or str(exc))
            return
        QMessageBox.critical(self, "Error", str(exc))
