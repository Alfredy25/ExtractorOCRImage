# [NUEVO] Ventana de login: solo widgets y flujo de UI. La llamada a login() vive en un
# hilo para no congelar la interfaz; HTTP y JWT siguen encapsulados en app.core.auth_client.

"""Diálogo de inicio de sesión contra el backend FastAPI."""

from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
)

from app.core.auth_client import AuthClientError, AuthError, login as do_login


class _LoginWorker(QThread):
    """Ejecuta do_login en segundo plano (httpx es bloqueante)."""

    succeeded = Signal()
    failed = Signal(str)

    def __init__(self, username: str, password: str, login_fn: Callable[[str, str], None]):
        super().__init__()
        self._username = username
        self._password = password
        self._login_fn = login_fn

    def run(self) -> None:
        try:
            self._login_fn(self._username, self._password)
        except AuthError as e:
            self.failed.emit(str(e))
            return
        except AuthClientError as e:
            self.failed.emit(str(e))
            return
        except Exception as e:
            self.failed.emit(f"Error inesperado: {e}")
            return
        self.succeeded.emit()


class LoginWindow(QDialog):
    """
    Formulario usuario / contraseña y botón Entrar.

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
        self._worker: Optional[_LoginWorker] = None

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Usuario:"))
        self._user = QLineEdit()
        self._user.setPlaceholderText("Nombre de usuario")
        layout.addWidget(self._user)

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

        self._user.returnPressed.connect(self._try_login)
        self._pass.returnPressed.connect(self._try_login)

    def _try_login(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            return

        self._error.hide()
        self._error.clear()
        u = self._user.text()
        p = self._pass.text()

        self._btn_login.setEnabled(False)
        self._btn_cancel.setEnabled(False)
        self._user.setEnabled(False)
        self._pass.setEnabled(False)

        self._worker = _LoginWorker(u, p, self._login_fn)
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
        self._user.setEnabled(True)
        self._pass.setEnabled(True)
        self._worker = None
