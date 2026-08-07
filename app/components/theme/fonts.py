"""Registro de las fuentes empaquetadas (Inter, JetBrains Mono, Material Symbols).

Las tres viajan en ``app/assets/fonts`` para no depender de lo que haya instalado
en la máquina del operador. Si algún archivo falta, se cae a fuentes del sistema
en lugar de romper el arranque.
"""

from __future__ import annotations

import logging

from PySide6.QtGui import QFont, QFontDatabase

from app.config import ASSETS_DIR

logger = logging.getLogger(__name__)

FONTS_DIR = ASSETS_DIR / "fonts"

SANS_FAMILY = "Inter"
MONO_FAMILY = "JetBrains Mono"
ICON_FAMILY = "Material Symbols Outlined"

SANS_FALLBACK = "Segoe UI"
MONO_FALLBACK = "Consolas"

_loaded_families: set[str] = set()
_fonts_registered = False


def load_app_fonts() -> set[str]:
    """Registra los .ttf empaquetados en QFontDatabase (idempotente).

    Debe llamarse con una ``QApplication`` ya creada. Devuelve el conjunto de
    familias disponibles.
    """
    global _fonts_registered
    if _fonts_registered:
        return set(_loaded_families)

    if not FONTS_DIR.is_dir():
        logger.warning("No existe la carpeta de fuentes: %s", FONTS_DIR)
        _fonts_registered = True
        return set()

    for ttf in sorted(FONTS_DIR.glob("*.ttf")):
        font_id = QFontDatabase.addApplicationFont(str(ttf))
        if font_id < 0:
            logger.warning("Qt no pudo cargar la fuente %s", ttf.name)
            continue
        _loaded_families.update(QFontDatabase.applicationFontFamilies(font_id))

    _fonts_registered = True
    logger.info("Fuentes cargadas: %s", sorted(_loaded_families) or "ninguna")
    return set(_loaded_families)


def sans_family() -> str:
    """Familia para texto de interfaz."""
    return SANS_FAMILY if SANS_FAMILY in _loaded_families else SANS_FALLBACK


def mono_family() -> str:
    """Familia monoespaciada para datos técnicos (CP, RFC, códigos)."""
    return MONO_FAMILY if MONO_FAMILY in _loaded_families else MONO_FALLBACK


def icons_available() -> bool:
    """Indica si la fuente de iconos se cargó correctamente."""
    return ICON_FAMILY in _loaded_families


def sans_font(size: int, weight: int = QFont.Weight.Normal) -> QFont:
    """Fuente de interfaz al tamaño en píxeles indicado."""
    font = QFont(sans_family())
    font.setPixelSize(size)
    font.setWeight(QFont.Weight(weight))
    return font


def mono_font(
    size: int,
    weight: int = QFont.Weight.Medium,
    letter_spacing: float = 0.0,
) -> QFont:
    """Fuente monoespaciada, con interletraje opcional.

    QSS no soporta ``letter-spacing``, así que las etiquetas técnicas en
    mayúsculas lo aplican por código.
    """
    font = QFont(mono_family())
    font.setPixelSize(size)
    font.setWeight(QFont.Weight(weight))
    if letter_spacing:
        font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 100 + letter_spacing)
    return font
