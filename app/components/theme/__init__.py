"""Sistema visual de la aplicación: tokens, fuentes, iconos y hoja de estilos.

Punto de entrada único: :func:`apply_theme`, que debe llamarse una vez creada la
``QApplication`` y antes de construir ventanas.
"""

from __future__ import annotations

import logging

from PySide6.QtWidgets import QApplication

from app.components.theme.fonts import (
    load_app_fonts,
    mono_family,
    mono_font,
    sans_family,
    sans_font,
)
from app.components.theme.icons import icon_char, icon_font, icon_pixmap, qicon
from app.components.theme.qss import build_palette, build_qss
from app.components.theme.tokens import (
    COLOR,
    FONT_SIZE,
    INSPECTOR_WIDTH,
    RADIUS,
    SIDEBAR_WIDTH,
    SPACE,
    TOPBAR_HEIGHT,
    rgba,
)

logger = logging.getLogger(__name__)

__all__ = [
    "COLOR",
    "FONT_SIZE",
    "INSPECTOR_WIDTH",
    "RADIUS",
    "SIDEBAR_WIDTH",
    "SPACE",
    "TOPBAR_HEIGHT",
    "apply_theme",
    "icon_char",
    "icon_font",
    "icon_pixmap",
    "mono_family",
    "mono_font",
    "qicon",
    "rgba",
    "sans_family",
    "sans_font",
]


def apply_theme() -> None:
    """Aplica fuentes, estilo base, paleta y hoja de estilos a la aplicación.

    Se fija el estilo «Fusion» a propósito: el estilo nativo de Windows ignora
    parte del QSS (bordes de campos, indicadores) y produce un resultado
    inconsistente con el diseño.
    """
    app = QApplication.instance()
    if app is None:
        logger.warning("apply_theme() sin QApplication activa; se omite el tema")
        return

    load_app_fonts()
    app.setStyle("Fusion")
    app.setPalette(build_palette())
    app.setFont(sans_font(FONT_SIZE["body_md"]))
    app.setStyleSheet(build_qss())
