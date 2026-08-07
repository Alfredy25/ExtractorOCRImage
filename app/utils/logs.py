"""Ubicación de los archivos de log de la aplicación."""

from __future__ import annotations

from pathlib import Path

from app.utils.paths import app_data_directory


def log_directory() -> Path:
    """Carpeta donde se escriben los logs (``%LOCALAPPDATA%\\ExtractorOCR\\logs``).

    La usan tanto el arranque, para configurar el handler rotatorio, como la
    interfaz, para abrir la carpeta desde la barra lateral.
    """
    return app_data_directory() / "logs"
