"""Glifos rasterizados para los subcontroles que QSS dibuja con imagen.

Al estilizar ``QComboBox::drop-down`` o los botones de un ``QSpinBox``, Qt deja de
pintar la flecha del estilo nativo y solo dibuja lo que indique la regla del
subcontrol, que necesita una imagen: no basta con un color. Aquí se guardan esos
glifos de la fuente de iconos como PNG en la caché del usuario y se devuelven
rutas listas para insertar en ``image: url(...)``.

Los archivos se reescriben en cada arranque para que no queden desincronizados si
la fuente de iconos se regenera con ``scripts/build_icon_font.py``.
"""

from __future__ import annotations

import logging
from pathlib import Path

from app.components.theme.icons import icon_char, icon_pixmap
from app.utils.paths import cache_directory

logger = logging.getLogger(__name__)

# Rutas ya escritas en esta ejecución, para no rasterizar el mismo glifo dos veces.
_written: dict[tuple[str, int, str], str | None] = {}


def _glyph_dir() -> Path:
    return cache_directory() / "glyphs"


def glyph_url(name: str, size: int, color: str) -> str | None:
    """Ruta del PNG del glifo lista para QSS, o ``None`` si no se pudo generar."""
    key = (name, size, color)
    if key in _written:
        return _written[key]

    path: str | None = None
    if icon_char(name):
        try:
            directory = _glyph_dir()
            directory.mkdir(parents=True, exist_ok=True)
            target = directory / f"{name}_{size}_{color.lstrip('#')}.png"
            if icon_pixmap(name, size, color).save(str(target), "PNG"):
                # QSS espera separadores «/» incluso en Windows.
                path = target.as_posix()
            else:
                logger.warning("No se pudo escribir el glifo %s en %s", name, target)
        except OSError as exc:
            logger.warning("No se pudo preparar el glifo %s: %s", name, exc)

    _written[key] = path
    return path


def glyph_image(name: str, size: int, color: str) -> str:
    """Declaración ``image`` de QSS para el glifo, o cadena vacía si no existe."""
    path = glyph_url(name, size, color)
    return f'image: url("{path}");' if path else ""
