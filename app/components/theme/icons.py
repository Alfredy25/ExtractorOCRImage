"""Iconos Material Symbols dibujados con la fuente empaquetada.

Los glifos se referencian por codepoint (no por ligadura de nombre) porque la
fuente recortada por ``scripts/build_icon_font.py`` no incluye tablas de
ligaduras. Si un nombre no está en la fuente, se registra y se devuelve vacío
para que la interfaz siga funcionando sin el icono.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap

from app.components.theme.fonts import ICON_FAMILY, icons_available
from app.components.theme.icon_codepoints import ICON_CODEPOINTS

logger = logging.getLogger(__name__)

_warned: set[str] = set()


def icon_char(name: str) -> str:
    """Carácter del icono, o cadena vacía si no está disponible."""
    if not icons_available():
        return ""
    char = ICON_CODEPOINTS.get(name)
    if char is None:
        if name not in _warned:
            _warned.add(name)
            logger.warning(
                "Icono %r no incluido; añádelo a ICON_NAMES en "
                "scripts/build_icon_font.py y regenera la fuente",
                name,
            )
        return ""
    return char


def icon_font(size: int) -> QFont:
    """Fuente de iconos al tamaño en píxeles indicado."""
    font = QFont(ICON_FAMILY)
    font.setPixelSize(size)
    return font


def icon_pixmap(name: str, size: int, color: str, gap: int = 0) -> QPixmap:
    """Dibuja el glifo en un pixmap transparente del color indicado.

    ``gap`` reserva píxeles transparentes a la derecha del glifo. Es la forma de
    separar el icono del texto en un botón: Qt no expone ese hueco ni por QSS ni
    por API, así que se hornea en la propia imagen.
    """
    pixmap = QPixmap(QSize(size + gap, size))
    pixmap.fill(Qt.GlobalColor.transparent)
    char = icon_char(name)
    if not char:
        return pixmap
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    painter.setPen(QColor(color))
    painter.setFont(icon_font(size))
    painter.drawText(QRect(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, char)
    painter.end()
    return pixmap


def qicon(name: str, size: int, color: str, gap: int = 0) -> QIcon:
    """``QIcon`` a partir de un glifo, para botones, acciones o ventanas."""
    return QIcon(icon_pixmap(name, size, color, gap))
