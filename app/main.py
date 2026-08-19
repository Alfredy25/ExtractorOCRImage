# [MODIFICADO] Arranque: login obligatorio contra FastAPI antes de abrir la ventana principal.

"""Punto de entrada de la aplicación."""
import logging
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog

from app.components.theme_manager import apply_theme
from app.config import API_BASE_URL
from app.utils.logs import log_directory
from app.views.login_window import LoginWindow
from app.views.main_window import MainWindow
from app.config import IMAGES_DIR
from PySide6.QtGui import QIcon

# Identidad ante la barra de tareas de Windows (no es el nombre del proceso).
_WINDOWS_APP_ID = "FGC.ExtractorOCR"


def _set_windows_app_user_model_id(app_id: str) -> None:
    """Declara quién es esta app para que Windows no la mezcle con python.exe."""
    if sys.platform != "win32":
        return
    try:
        from ctypes import windll

        windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except (AttributeError, OSError):
        return


def setup_logging() -> Path:
    """Configura logging con RotatingFileHandler."""
    log_dir = log_directory()
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "extractor_ocr.log"

    from logging.handlers import RotatingFileHandler

    handler = RotatingFileHandler(log_file, maxBytes=2 * 1024 * 1024, backupCount=3)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)

    # También a consola en desarrollo
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(formatter)
    root.addHandler(console)
    return log_file


def main():
    log_file = setup_logging()
    log = logging.getLogger("app.main")
    log.info("Log file: %s", log_file)
    log.info("Backend API: %s", API_BASE_URL)

    # Debe ir antes de QApplication: Windows agrupa la ventana con este ID.
    _set_windows_app_user_model_id(_WINDOWS_APP_ID)

    # Alta DPI: debe llamarse antes de crear QApplication
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(str(IMAGES_DIR/"extractor_ocr.png")))
    app.setApplicationName("Extractor OCR")
    app.setApplicationDisplayName("Extractor OCR - Destinatarios")

    apply_theme()

    # Sin sesión válida no se abre la app de extracción (JWT queda en auth_client).
    login_dlg = LoginWindow()
    if login_dlg.exec() != QDialog.DialogCode.Accepted:
        return 0

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
