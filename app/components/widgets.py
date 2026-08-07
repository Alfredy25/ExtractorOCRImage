"""Bloques visuales reutilizables del sistema de diseño.

Todos los componentes declaran su intención mediante propiedades Qt
(``variant``, ``role``, ``tone``) y dejan la apariencia en manos de la hoja de
estilos de :mod:`app.components.theme`. Aquí solo vive lo que QSS no puede
expresar: fuentes con interletraje, brillos y composición de layouts.
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QIcon
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.components.theme import (
    COLOR,
    FONT_SIZE,
    SPACE,
    icon_char,
    icon_font,
    mono_font,
    qicon,
)

# Interletraje de las etiquetas técnicas (0.05em en el diseño de referencia).
_MONO_TRACKING = 5.0


def set_property(widget: QWidget, name: str, value) -> None:
    """Asigna una propiedad de estilo y refresca el widget.

    Cambiar una propiedad usada por la hoja de estilos no repinta el widget por
    sí solo; hay que forzar el ciclo unpolish/polish.
    """
    widget.setProperty(name, value)
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


# --- Etiquetas -----------------------------------------------------------


def icon_label(name: str, size: int = 20, role: str = "cardIcon") -> QLabel:
    """Icono como etiqueta (no interactivo)."""
    label = QLabel(icon_char(name))
    label.setProperty("role", role)
    label.setFont(icon_font(size))
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setFixedSize(size + 4, size + 4)
    return label


def section_label(text: str) -> QLabel:
    """Encabezado de sección: monoespaciada, mayúsculas, espaciado amplio."""
    label = QLabel(text.upper())
    label.setProperty("role", "sectionLabel")
    label.setFont(mono_font(FONT_SIZE["label_md"], letter_spacing=_MONO_TRACKING))
    return label


def field_label(text: str) -> QLabel:
    """Etiqueta de campo de formulario."""
    label = QLabel(text)
    label.setProperty("role", "fieldLabel")
    label.setFont(mono_font(FONT_SIZE["label_sm"]))
    return label


def card_title(text: str) -> QLabel:
    """Título de tarjeta."""
    label = QLabel(text)
    label.setProperty("role", "cardTitle")
    return label


def subtitle(text: str) -> QLabel:
    """Texto secundario de apoyo."""
    label = QLabel(text)
    label.setProperty("role", "subtitle")
    label.setWordWrap(True)
    return label


def chip(text: str, tone: str = "primary") -> QLabel:
    """Etiqueta compacta de estado o metadato."""
    label = QLabel(text)
    label.setProperty("role", "chip")
    label.setProperty("tone", tone)
    label.setFont(mono_font(FONT_SIZE["label_sm"], letter_spacing=_MONO_TRACKING))
    return label


def divider(soft: bool = False) -> QFrame:
    """Línea separadora horizontal."""
    line = QFrame()
    line.setProperty("role", "dividerSoft" if soft else "divider")
    line.setFixedHeight(1)
    return line


def vertical_divider(object_name: str = "ViewerHudSeparator") -> QFrame:
    """Línea separadora vertical (barra de herramientas)."""
    line = QFrame()
    line.setObjectName(object_name)
    line.setFixedWidth(1)
    return line


# --- Botones -------------------------------------------------------------


def icon_button(
    name: str,
    tooltip: str,
    variant: str = "icon",
    size: int = 18,
    checkable: bool = False,
) -> QPushButton:
    """Botón solo-icono con tooltip obligatorio (accesibilidad mínima)."""
    button = QPushButton(icon_char(name))
    button.setProperty("variant", variant)
    button.setFont(icon_font(size))
    button.setToolTip(tooltip)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setCheckable(checkable)
    return button


# Color del icono según la variante del botón: debe contrastar con su fondo.
_ICON_COLOR_BY_VARIANT = {
    "primary": "on_primary_container",
    "ghost": "on_surface_variant",
    "link": "primary",
    "nav": "on_surface_variant",
}

# Hueco entre el icono y el texto de un botón (ver ``icon_pixmap``).
_ICON_GAP = 6


def _button_icon(name: str, size: int, color_key: str) -> QIcon:
    return qicon(name, size, COLOR[color_key], gap=_ICON_GAP)


def text_button(
    text: str,
    variant: str = "ghost",
    icon: str | None = None,
    tone: str | None = None,
    icon_size: int = 18,
) -> QPushButton:
    """Botón con texto y, opcionalmente, icono a la izquierda.

    El icono se pasa como ``QIcon`` (glifo rasterizado) en lugar de mezclarlo en
    el texto: así se controla su tamaño, que si no quedaría atado al de la letra.
    """
    button = QPushButton(text)
    button.setProperty("variant", variant)
    if tone:
        button.setProperty("tone", tone)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    if icon:
        color_key = "error" if tone == "danger" else _ICON_COLOR_BY_VARIANT.get(variant, "on_surface")
        button.setIcon(_button_icon(icon, icon_size, color_key))
        button.setIconSize(QSize(icon_size + _ICON_GAP, icon_size))
    return button


def nav_button(text: str, icon: str, tone: str | None = None) -> QPushButton:
    """Elemento de navegación de la barra lateral (checkable y exclusivo)."""
    button = text_button(text, variant="nav", icon=icon, tone=tone, icon_size=20)
    button.setCheckable(True)
    button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    button.setMinimumHeight(36)
    if icon_char(icon):
        # El estado activo invierte el fondo, así que el icono cambia de color
        # con él (un QIcon no hereda el color del texto).
        idle = _button_icon(icon, 20, "error" if tone == "danger" else "on_surface_variant")
        active = _button_icon(icon, 20, "on_secondary_container")
        button.toggled.connect(
            lambda checked, b=button: b.setIcon(active if checked else idle)
        )
    return button


# --- Efectos -------------------------------------------------------------


def apply_glow(widget: QWidget, color_key: str = "primary_container", radius: int = 18) -> None:
    """Halo de acento alrededor del widget.

    Equivale a la clase ``glow-primary`` de los diseños: QSS no tiene
    ``box-shadow``, así que se usa un efecto gráfico.
    """
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(radius)
    effect.setOffset(0, 0)
    glow = QColor(COLOR[color_key])
    glow.setAlpha(140)
    effect.setColor(glow)
    widget.setGraphicsEffect(effect)


# --- Contenedores --------------------------------------------------------


class Card(QFrame):
    """Contenedor de contenido con cabecera opcional (icono + título + extras).

    Es el contenedor base de las tres pantallas: envuelve el cuerpo en un
    ``QFrame`` propio para que la cabecera conserve su tono y las esquinas
    redondeadas.
    """

    def __init__(
        self,
        title: str | None = None,
        icon: str | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setObjectName("Card")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._header: QFrame | None = None
        self._header_layout: QHBoxLayout | None = None
        if title is not None:
            self._header = QFrame()
            self._header.setObjectName("CardHeader")
            self._header.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            self._header_layout = QHBoxLayout(self._header)
            self._header_layout.setContentsMargins(
                SPACE["md"], SPACE["sm"] + 2, SPACE["md"], SPACE["sm"] + 2
            )
            self._header_layout.setSpacing(SPACE["sm"])
            if icon:
                self._header_layout.addWidget(icon_label(icon, FONT_SIZE["headline_sm"]))
            self._title_label = card_title(title)
            self._header_layout.addWidget(self._title_label)
            self._header_layout.addStretch(1)
            outer.addWidget(self._header)

        body = QFrame()
        body.setObjectName("CardBody")
        self._body_layout = QVBoxLayout(body)
        self._body_layout.setContentsMargins(
            SPACE["md"], SPACE["md"], SPACE["md"], SPACE["md"]
        )
        self._body_layout.setSpacing(SPACE["sm"] + 4)
        outer.addWidget(body, 1)

    @property
    def body(self) -> QVBoxLayout:
        """Layout donde añadir el contenido de la tarjeta."""
        return self._body_layout

    def add_header_widget(self, widget: QWidget) -> None:
        """Añade un widget al extremo derecho de la cabecera."""
        if self._header_layout is None:
            raise RuntimeError("La tarjeta se creó sin cabecera")
        self._header_layout.addWidget(widget)

    def set_body_margins(self, left: int, top: int, right: int, bottom: int) -> None:
        self._body_layout.setContentsMargins(left, top, right, bottom)

    def set_title(self, text: str) -> None:
        if self._header_layout is not None:
            self._title_label.setText(text)


class Banner(QFrame):
    """Aviso destacado con icono, título y descripción (éxito / error / neutro)."""

    def __init__(
        self,
        icon: str,
        title: str,
        message: str = "",
        tone: str = "success",
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setObjectName("Banner")
        self.setProperty("tone", tone)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(SPACE["md"], SPACE["sm"] + 4, SPACE["md"], SPACE["sm"] + 4)
        layout.setSpacing(SPACE["md"])

        self._icon = icon_label(icon, 26, role="cardIcon")
        layout.addWidget(self._icon, 0, Qt.AlignmentFlag.AlignTop)

        text_column = QVBoxLayout()
        text_column.setSpacing(2)
        self._title = card_title(title)
        text_column.addWidget(self._title)
        self._message = subtitle(message)
        self._message.setVisible(bool(message))
        text_column.addWidget(self._message)
        layout.addLayout(text_column, 1)

    def set_message(self, text: str) -> None:
        self._message.setText(text)
        self._message.setVisible(bool(text))

    def set_title(self, text: str) -> None:
        self._title.setText(text)


def labeled_field(label_text: str, field: QWidget, mono: bool = False) -> QWidget:
    """Campo de formulario con su etiqueta encima."""
    container = QWidget()
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(SPACE["xs"])
    layout.addWidget(field_label(label_text))
    if mono:
        field.setProperty("role", "mono")
    layout.addWidget(field)
    return container
