# [MODIFICADO] Arranque: login obligatorio contra FastAPI antes de abrir la ventana principal.

"""Punto de entrada de la aplicación."""
import logging
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog

from app.config import API_BASE_URL, APP_ROOT
from app.ui.login_window import LoginWindow
from app.ui.main_window import MainWindow
from app.ui.themes import apply_theme, get_saved_theme


def setup_logging():
    """Configura logging con RotatingFileHandler."""
    log_dir = APP_ROOT.parent / "logs"
    log_dir.mkdir(exist_ok=True)
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


def main():
    setup_logging()
    log = logging.getLogger("app.main")
    log.info("Backend API: %s", API_BASE_URL)

    # Alta DPI: debe llamarse antes de crear QApplication
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("Extractor OCR")
    app.setApplicationDisplayName("Extractor OCR - Destinatarios")

    apply_theme(get_saved_theme())

    # Sin sesión válida no se abre la app de extracción (JWT queda en auth_client).
    login_dlg = LoginWindow()
    if login_dlg.exec() != QDialog.DialogCode.Accepted:
        return 0

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
