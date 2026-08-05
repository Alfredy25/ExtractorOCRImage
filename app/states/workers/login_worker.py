"""Worker de autenticación para no bloquear el hilo de la interfaz."""

from typing import Callable

from PySide6.QtCore import QThread, Signal

from app.services.auth_service import AuthClientError, AuthError


class LoginWorker(QThread):
    """Ejecuta una función de login bloqueante en segundo plano."""

    succeeded = Signal()
    failed = Signal(str)

    def __init__(self, email: str, password: str,
                 login_fn: Callable[[str, str], None]):
        super().__init__()
        self._email = email
        self._password = password
        self._login_fn = login_fn

    def run(self) -> None:
        try:
            self._login_fn(self._email, self._password)
        except (AuthError, AuthClientError) as exc:
            self.failed.emit(str(exc))
            return
        except Exception as exc:
            self.failed.emit(f"Error inesperado: {exc}")
            return
        self.succeeded.emit()
