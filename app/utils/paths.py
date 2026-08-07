"""Rutas de datos por usuario.

Todo lo que la aplicación escribe en tiempo de ejecución (logs, caché) vive aquí
y no dentro del paquete: al empaquetar con PyInstaller el paquete se extrae en una
carpeta temporal y no sirve como almacenamiento.
"""

from __future__ import annotations

import os
from pathlib import Path

APP_FOLDER_NAME = "ExtractorOCR"


def app_data_directory() -> Path:
    """Carpeta de la aplicación en el perfil del usuario.

    En Windows, ``%LOCALAPPDATA%\\ExtractorOCR``; si la variable no existe, se
    reconstruye desde el directorio personal.
    """
    local_appdata = os.getenv("LOCALAPPDATA")
    base = Path(local_appdata) if local_appdata else Path.home() / "AppData" / "Local"
    return base / APP_FOLDER_NAME


def cache_directory() -> Path:
    """Caché regenerable (por ejemplo, los glifos que QSS necesita como imagen)."""
    return app_data_directory() / "cache"
