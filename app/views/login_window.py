# [NUEVO] Ventana de login: solo widgets y flujo de UI. La llamada a login() vive en un
# hilo para no congelar la interfaz; HTTP y JWT quedan en api, services y states.

"""Diálogo de inicio de sesión contra el backend FastAPI."""

from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                                QLabel, QLineEdit, QPushButton)

from app.services.auth_service import login as do_login
from app.states.workers.login_worker import LoginWorker


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
        self.resize(400, 220)
        self.setMinimumWidth(360)

        self._login_fn = login_fn or do_login
        self._worker: Optional[LoginWorker] = None

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Correo electrónico:"))
        self._email = QLineEdit()
        self._email.setPlaceholderText("user@example.com")
        layout.addWidget(self._email)

        layout.addWidget(QLabel("Contraseña:"))
        self._pass = QLineEdit()
        self._pass.setEchoMode(QLineEdit.EchoMode.Password)
        self._pass.setPlaceholderText("Contraseña")
        layout.addWidget(self._pass)

        self._error = QLabel("")
        self._error.setWordWrap(True)
        self._error.setStyleSheet("color: #b00020;")
        self._error.hide()
        layout.addWidget(self._error)

        row = QHBoxLayout()
        row.addStretch()
        self._btn_login = QPushButton("Iniciar sesión")
        self._btn_login.setDefault(True)
        self._btn_login.clicked.connect(self._try_login)
        row.addWidget(self._btn_login)
        self._btn_cancel = QPushButton("Salir")
        self._btn_cancel.clicked.connect(self.reject)
        row.addWidget(self._btn_cancel)
        layout.addLayout(row)

        self._email.returnPressed.connect(self._try_login)
        self._pass.returnPressed.connect(self._try_login)

    def _try_login(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            return

        self._error.hide()
        self._error.clear()
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
        self._error.setText(message)
        self._error.show()

    def _on_worker_finished(self) -> None:
        self._btn_login.setEnabled(True)
        self._btn_cancel.setEnabled(True)
        self._email.setEnabled(True)
        self._pass.setEnabled(True)
        self._worker = None
