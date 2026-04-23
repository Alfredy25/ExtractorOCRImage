"""Punto de entrada de la aplicación."""
import logging
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from app.config import APP_ROOT, get_db_summary_for_logs
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
    logging.getLogger("app.main").info(
        "Base de datos: %s", get_db_summary_for_logs()
    )
    # Alta DPI: debe llamarse antes de crear QApplication
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("Extractor OCR")
    app.setApplicationDisplayName("Extractor OCR - Destinatarios")

    apply_theme(get_saved_theme())

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
