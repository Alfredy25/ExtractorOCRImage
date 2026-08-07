"""Design tokens del sistema visual «Logistics Technical Suite» (modo oscuro).

Fuente de verdad para colores, espaciado, radios y escala tipográfica. Cualquier
color nuevo se declara aquí; los widgets no deben incrustar hex sueltos.
"""

from __future__ import annotations

# --- Color ---------------------------------------------------------------
# Paleta Material 3 sobre base azul-marino profundo. Los nombres siguen los
# roles de Material (surface / on-surface / primary / container…) para que el
# mapeo con los diseños de referencia sea directo.
COLOR: dict[str, str] = {
    # Superficies: la profundidad se comunica por capas tonales, no por sombras.
    "background": "#10131b",
    "surface": "#10131b",
    "surface_dim": "#10131b",
    "surface_bright": "#363941",
    "surface_container_lowest": "#0a0e15",
    "surface_container_low": "#181c23",
    "surface_container": "#1c2027",
    "surface_container_high": "#262a32",
    "surface_container_highest": "#31353d",
    "surface_variant": "#31353d",
    # Texto e iconografía
    "on_surface": "#e0e2ec",
    "on_surface_variant": "#c0c6d6",
    "inverse_surface": "#e0e2ec",
    "inverse_on_surface": "#2d3038",
    # Bordes
    "outline": "#8a91a0",
    "outline_variant": "#404754",
    # Acento principal
    "primary": "#a9c7ff",
    "on_primary": "#003063",
    "primary_container": "#3a90ff",
    "on_primary_container": "#002957",
    "primary_fixed": "#d6e3ff",
    "inverse_primary": "#005db6",
    # Acento secundario
    "secondary": "#b0c6ff",
    "on_secondary": "#002c6f",
    "secondary_container": "#578cff",
    "on_secondary_container": "#002662",
    # Acento terciario (avisos, datos destacados)
    "tertiary": "#ffb691",
    "on_tertiary": "#552100",
    "tertiary_container": "#eb6b13",
    "on_tertiary_container": "#4a1c00",
    # OCR: DESIGN.md reserva estos tonos para el recorte y las cajas de extracción.
    "ocr_selection": "#69b4ff",
    "ocr_selection_fill": "#0085ff",
    # Error
    "error": "#ffb4ab",
    "on_error": "#690005",
    "error_container": "#93000a",
    "on_error_container": "#ffdad6",
}

# Estados interactivos derivados del acento (QSS no calcula luminosidad).
COLOR.update(
    {
        "primary_container_hover": "#5aa4ff",
        "primary_container_pressed": "#2b7fe6",
        "secondary_container_hover": "#6f9dff",
        "error_container_hover": "#b3141f",
    }
)


def rgba(color_key: str, alpha: float) -> str:
    """Devuelve un color de la paleta como ``rgba(...)`` para QSS.

    QSS no admite opacidad sobre hex, así que los tintes translúcidos (chips,
    superposiciones, relleno del recorte) se expresan con esta función.
    """
    hex_value = COLOR.get(color_key, color_key).lstrip("#")
    if len(hex_value) != 6:
        raise ValueError(f"Color no válido para rgba(): {color_key!r}")
    r, g, b = (int(hex_value[i : i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r}, {g}, {b}, {alpha:.3f})"


# --- Espaciado (base 4 px) ----------------------------------------------
SPACE = {"xs": 4, "sm": 8, "md": 16, "lg": 24, "xl": 32}

# --- Radios --------------------------------------------------------------
# Lenguaje de formas «soft»: controles sutiles, tarjetas algo más redondeadas.
RADIUS = {
    "control": 4,  # inputs y botones
    "card": 8,  # tarjetas y contenedores
    "pill": 12,  # chips y botones circulares
}

# --- Tipografía ----------------------------------------------------------
# Inter para interfaz, JetBrains Mono para datos técnicos (CP, RFC, códigos).
FONT_SIZE = {
    "headline_lg": 28,
    "headline_md": 22,
    "headline_sm": 17,
    "body_lg": 16,
    "body_md": 14,
    "body_sm": 13,
    "label_md": 12,  # etiquetas de sección (mono, mayúsculas)
    "label_sm": 11,  # etiquetas de campo (mono)
}

FONT_WEIGHT = {"regular": 400, "medium": 500, "semibold": 600, "bold": 700}

# Anchos fijos del shell (DESIGN.md: barra lateral 280 px, inspector 400 px).
SIDEBAR_WIDTH = 280
INSPECTOR_WIDTH = 400
TOPBAR_HEIGHT = 68
