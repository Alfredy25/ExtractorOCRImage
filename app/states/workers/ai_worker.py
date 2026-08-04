"""Worker para ejecutar OCR sin bloquear el hilo de la interfaz."""

import logging

from PySide6.QtCore import QThread, Signal

from app.services.ocr_service import extract_fields

logger = logging.getLogger(__name__)


class AIWorker(QThread):
    """Ejecuta la llamada a IA en segundo plano."""

    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, image_np, sede: str):
        super().__init__()
        self._image = image_np
        self._sede = sede

    def run(self) -> None:
        try:
            result = extract_fields(self._image, self._sede)
            self.finished.emit(result)
        except Exception as exc:
            logger.exception("Error en llamada IA")
            self.error.emit(str(exc))
