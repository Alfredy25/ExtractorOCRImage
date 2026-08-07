"""Diálogo de inicio de sesión contra el backend FastAPI.

Solo widgets y flujo de UI: la llamada a ``login()`` vive en un hilo para no
congelar la interfaz, y HTTP y JWT quedan en ``api``, ``services`` y ``states``.
"""

from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from app.components.theme import COLOR, FONT_SIZE, SPACE, qicon
from app.components.widgets import (
    apply_glow,
    field_label,
    icon_label,
    subtitle,
    text_button,
)
from app.services.auth_service import login as do_login
from app.states.workers.login_worker import LoginWorker

_CARD_WIDTH = 420


class LoginWindow(QDialog):
    """
    Formulario correo electrónico / contraseña y botón Entrar.

    Al autenticación correcta cierra con ``accept()``; el JWT queda en memoria en
    ``auth_client`` (la UI no lee ni guarda el token).
    """

    def __init__(self, parent=None, login_fn: Optional[Callable[[str, str], None]] = None):
        super().__init__(parent)
        self.setWindowTitle("Iniciar sesión")
        self.setModal(True)
        self.resize(520, 620)
        self.setMinimumWidth(460)

        self._login_fn = login_fn or do_login
        self._worker: Optional[LoginWorker] = None

        self._setup_ui()

    # --- Construcción --------------------------------------------------

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(SPACE["xl"], SPACE["xl"], SPACE["xl"], SPACE["lg"])
        root.setSpacing(SPACE["md"])

        root.addStretch(1)

        centered = QHBoxLayout()
        centered.addStretch(1)
        centered.addWidget(self._build_card())
        centered.addStretch(1)
        root.addLayout(centered)

        root.addStretch(1)

        footer = QLabel("© Extractor OCR · Destinatarios")
        footer.setObjectName("LoginFooter")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(footer)

    def _build_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("LoginCard")
        card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        card.setFixedWidth(_CARD_WIDTH)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(SPACE["xl"], SPACE["xl"], SPACE["xl"], SPACE["xl"])
        layout.setSpacing(SPACE["md"])

        layout.addWidget(self._build_logo(), 0, Qt.AlignmentFlag.AlignHCenter)

        title = QLabel("Bienvenido")
        title.setProperty("role", "headline")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        caption = subtitle("Inicia sesión para acceder al espacio de trabajo OCR")
        caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(caption)

        layout.addSpacing(SPACE["xs"])

        layout.addWidget(field_label("Correo electrónico"))
        self._email = QLineEdit()
        self._email.setPlaceholderText("usuario@example.com")
        self._email.setMinimumHeight(38)
        self._email.addAction(
            qicon("mail", FONT_SIZE["body_lg"], COLOR["on_surface_variant"]),
            QLineEdit.ActionPosition.LeadingPosition,
        )
        layout.addWidget(self._email)

        layout.addWidget(field_label("Contraseña"))
        self._pass = QLineEdit()
        self._pass.setEchoMode(QLineEdit.EchoMode.Password)
        self._pass.setPlaceholderText("••••••••")
        self._pass.setMinimumHeight(38)
        self._pass.addAction(
            qicon("lock", FONT_SIZE["body_lg"], COLOR["on_surface_variant"]),
            QLineEdit.ActionPosition.LeadingPosition,
        )
        layout.addWidget(self._pass)

        self._error = self._build_error_banner()
        layout.addWidget(self._error)

        layout.addSpacing(SPACE["xs"])

        self._btn_login = text_button("Iniciar sesión", variant="primary", icon="login")
        self._btn_login.setMinimumHeight(42)
        self._btn_login.setDefault(True)
        self._btn_login.clicked.connect(self._try_login)
        layout.addWidget(self._btn_login)
        apply_glow(self._btn_login)

        self._btn_cancel = text_button("Salir", variant="link")
        self._btn_cancel.clicked.connect(self.reject)
        layout.addWidget(self._btn_cancel, 0, Qt.AlignmentFlag.AlignHCenter)

        self._email.returnPressed.connect(self._try_login)
        self._pass.returnPressed.connect(self._try_login)
        return card

    @staticmethod
    def _build_logo() -> QFrame:
        logo = QFrame()
        logo.setObjectName("LoginLogo")
        logo.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        logo.setFixedSize(64, 64)
        layout = QVBoxLayout(logo)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(
            icon_label("document_scanner", 32), 0, Qt.AlignmentFlag.AlignCenter
        )
        return logo

    def _build_error_banner(self) -> QWidget:
        banner = QFrame()
        banner.setObjectName("LoginErrorBanner")
        banner.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        layout = QHBoxLayout(banner)
        layout.setContentsMargins(SPACE["sm"] + 2, SPACE["sm"], SPACE["sm"] + 2, SPACE["sm"])
        layout.setSpacing(SPACE["sm"])

        icon = icon_label("error", 18, role="cardIcon")
        icon.setStyleSheet(f"color: {COLOR['error']};")
        layout.addWidget(icon, 0, Qt.AlignmentFlag.AlignTop)

        self._error_text = QLabel("")
        self._error_text.setProperty("role", "errorText")
        self._error_text.setWordWrap(True)
        layout.addWidget(self._error_text, 1)

        banner.hide()
        return banner

    # --- Flujo de login ------------------------------------------------

    def _try_login(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            return

        self._error.hide()
        self._error_text.clear()
        email = self._email.text()
        p = self._pass.text()

        self._btn_login.setEnabled(False)
        self._btn_cancel.setEnabled(False)
        self._email.setEnabled(False)
        self._pass.setEnabled(False)

        self._worker = LoginWorker(email, p, self._login_fn)
        self._worker.succeeded.connect(self._on_success)
        self._worker.failed.connect(self._on_failure)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.start()

    def _on_success(self) -> None:
        self.accept()

    def _on_failure(self, message: str) -> None:
        self._error_text.setText(message)
        self._error.show()

    def _on_worker_finished(self) -> None:
        self._btn_login.setEnabled(True)
        self._btn_cancel.setEnabled(True)
        self._email.setEnabled(True)
        self._pass.setEnabled(True)
        self._worker = None
