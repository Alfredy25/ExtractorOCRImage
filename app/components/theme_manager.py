"""Fachada del sistema visual (tema oscuro «Logistics Technical Suite»).

La implementación vive en el paquete :mod:`app.components.theme`, repartida en
tokens, fuentes, iconos y hoja de estilos. Este módulo se conserva porque es la
ruta de importación histórica del tema en el proyecto.

La aplicación tiene un único tema; el modo cálido anterior se retiró al adoptar
el diseño de referencia, que es dark-mode.
"""

from app.components.theme import COLOR, apply_theme, icon_char, rgba

__all__ = ["COLOR", "apply_theme", "icon_char", "rgba"]
