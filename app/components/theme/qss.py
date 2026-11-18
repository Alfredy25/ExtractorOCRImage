"""Construcción de la hoja de estilos y la paleta Qt a partir de los tokens.

El estilo se apoya en selectores por *propiedad* (``variant``, ``role``) en lugar
de hojas de estilo incrustadas widget a widget: así los componentes solo declaran
su intención (``variant="primary"``) y la apariencia vive centralizada aquí.

Limitaciones de QSS frente a los diseños en Tailwind:

- No existe ``box-shadow`` ni desenfoque: la profundidad se logra por capas
  tonales y bordes, y los brillos puntuales con ``QGraphicsDropShadowEffect``.
- No existe opacidad sobre hex: los tintes se expresan con ``rgba()``.
- No hay transiciones: los estados ``:hover`` cambian de golpe.
- No existe ``letter-spacing``: se aplica por código donde hace falta.
- Los subcontroles nativos (flechas de combos y spinners, marca de selección) se
  dibujan con imagen: ver :func:`_subcontrols_qss`.
"""

from __future__ import annotations

from PySide6.QtGui import QColor, QPalette

from app.components.theme.fonts import mono_family, sans_family
from app.components.theme.glyph_assets import glyph_image
from app.components.theme.icons import icon_char
from app.components.theme.tokens import (
    COLOR,
    FONT_SIZE,
    RADIUS,
    SIDEBAR_WIDTH,
    TOPBAR_HEIGHT,
    rgba,
)


def build_palette() -> QPalette:
    """Paleta oscura para lo que Qt dibuja de forma nativa.

    Las flechas de ``QComboBox``/``QSpinBox``, los marcos de foco y el texto
    deshabilitado los pinta el estilo con la paleta, no con QSS; sin esto
    quedarían con los colores claros por defecto.
    """
    palette = QPalette()
    window = QColor(COLOR["background"])
    base = QColor(COLOR["surface_dim"])
    text = QColor(COLOR["on_surface"])
    disabled = QColor(COLOR["outline"])

    palette.setColor(QPalette.ColorRole.Window, window)
    palette.setColor(QPalette.ColorRole.WindowText, text)
    palette.setColor(QPalette.ColorRole.Base, base)
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(COLOR["surface_container"]))
    palette.setColor(QPalette.ColorRole.Text, text)
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(COLOR["outline"]))
    palette.setColor(QPalette.ColorRole.Button, QColor(COLOR["surface_container_high"]))
    palette.setColor(QPalette.ColorRole.ButtonText, text)
    palette.setColor(QPalette.ColorRole.BrightText, QColor(COLOR["error"]))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(COLOR["primary_container"]))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(COLOR["on_primary_container"]))
    palette.setColor(QPalette.ColorRole.Link, QColor(COLOR["primary"]))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(COLOR["surface_container_highest"]))
    palette.setColor(QPalette.ColorRole.ToolTipText, text)

    for role in (QPalette.ColorRole.WindowText, QPalette.ColorRole.Text,
                    QPalette.ColorRole.ButtonText):
        palette.setColor(QPalette.ColorGroup.Disabled, role, disabled)

    return palette


def _subcontrols_qss() -> str:
    """Flechas de combos y spinners, y marca de los checkbox.

    Qt no reutiliza la flecha del estilo nativo cuando el QSS interviene en estos
    subcontroles: hay que darle una imagen. Si la fuente de iconos no está
    disponible se devuelve una hoja vacía a propósito, para que el estilo nativo
    siga dibujando sus flechas en lugar de dejar los combos indistinguibles de un
    campo de texto.
    """
    if not icon_char("expand_more"):
        return "/* Sin fuente de iconos: se conservan las flechas nativas. */"

    c = COLOR
    arrow = glyph_image("expand_more", 16, c["on_surface_variant"])
    arrow_off = glyph_image("expand_more", 16, c["outline"])
    up_small = glyph_image("expand_less", 12, c["on_surface_variant"])
    down_small = glyph_image("expand_more", 12, c["on_surface_variant"])
    check = glyph_image("check", 14, c["on_primary_container"])

    # Los controles se listan por tipo en lugar de usar «QAbstractSpinBox» porque
    # los dos grupos necesitan geometrías distintas: el desplegable de fecha pinta
    # un galón único a la derecha y los campos de hora, dos flechas apiladas.
    return f"""
QComboBox::drop-down, QDateEdit::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 22px;
    border: none;
    background-color: transparent;
}}
QComboBox::down-arrow, QDateEdit::down-arrow {{
    {arrow}
    width: 16px;
    height: 16px;
}}
QComboBox::down-arrow:disabled, QDateEdit::down-arrow:disabled {{
    {arrow_off}
}}

QSpinBox::up-button, QDoubleSpinBox::up-button, QTimeEdit::up-button {{
    subcontrol-origin: border;
    subcontrol-position: top right;
}}
QSpinBox::down-button, QDoubleSpinBox::down-button, QTimeEdit::down-button {{
    subcontrol-origin: border;
    subcontrol-position: bottom right;
}}
QSpinBox::up-button, QDoubleSpinBox::up-button, QTimeEdit::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button, QTimeEdit::down-button {{
    width: 18px;
    margin: 1px 2px;
    border: none;
    border-radius: 2px;
    background-color: transparent;
}}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QTimeEdit::up-button:hover, QSpinBox::down-button:hover,
QDoubleSpinBox::down-button:hover, QTimeEdit::down-button:hover {{
    background-color: {c["surface_container_high"]};
}}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow, QTimeEdit::up-arrow {{
    {up_small}
    width: 12px;
    height: 12px;
}}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow, QTimeEdit::down-arrow {{
    {down_small}
    width: 12px;
    height: 12px;
}}

QCheckBox::indicator:checked {{
    {check}
}}
"""


def build_qss() -> str:
    """Hoja de estilos completa de la aplicación."""
    c = COLOR
    r = RADIUS
    sans = sans_family()
    mono = mono_family()

    return f"""
/* ---------- Base ---------------------------------------------------- */
/* Deliberadamente NO se fija fondo en «QWidget»: dejarlo transparente es lo
   que permite que las tarjetas se vean como tarjetas y no como rectángulos
   planos superpuestos. */
QMainWindow, QDialog {{
    background-color: {c["background"]};
}}
QWidget {{
    color: {c["on_surface"]};
}}
QWidget:disabled {{
    color: {c["outline"]};
}}

/* ---------- Shell: barra lateral, barra superior, contenido ---------- */
#Sidebar {{
    background-color: {c["surface_dim"]};
    border: none;
    border-right: 1px solid {c["outline_variant"]};
    min-width: {SIDEBAR_WIDTH}px;
    max-width: {SIDEBAR_WIDTH}px;
}}
#TopBar {{
    background-color: {c["surface_container"]};
    border: none;
    border-bottom: 1px solid {c["outline_variant"]};
    min-height: {TOPBAR_HEIGHT}px;
    max-height: {TOPBAR_HEIGHT}px;
}}
#ContentArea {{
    background-color: {c["background"]};
    border: none;
}}
#SidebarBrand {{
    background-color: {c["surface_container_high"]};
    border: 1px solid {c["outline_variant"]};
    border-radius: {r["card"]}px;
}}
QFrame[role="divider"] {{
    background-color: {c["outline_variant"]};
    border: none;
    max-height: 1px;
    min-height: 1px;
}}
QFrame[role="dividerSoft"] {{
    background-color: {c["surface_variant"]};
    border: none;
    max-height: 1px;
    min-height: 1px;
}}

/* ---------- Tarjetas ------------------------------------------------- */
QFrame#Card {{
    background-color: {c["surface_container"]};
    border: 1px solid {c["outline_variant"]};
    border-radius: {r["card"]}px;
}}
QFrame#CardHeader {{
    background-color: {c["surface_container_low"]};
    border: none;
    border-bottom: 1px solid {c["surface_variant"]};
    border-top-left-radius: {r["card"]}px;
    border-top-right-radius: {r["card"]}px;
}}
QFrame#CardBody {{
    background-color: transparent;
    border: none;
}}
/* Bloque de campos agrupados dentro de una tarjeta: un tono intermedio entre
   la tarjeta y los campos para escalonar la profundidad. */
QFrame#SectionBox {{
    background-color: {c["surface_container_low"]};
    border: 1px solid {rgba("outline_variant", 0.60)};
    border-radius: {r["card"]}px;
}}
QFrame#Banner {{
    background-color: {c["surface_container"]};
    border: 1px solid {c["outline_variant"]};
    border-radius: {r["card"]}px;
}}
QFrame#Banner[tone="success"] {{
    border: 1px solid {rgba("secondary_container", 0.55)};
    background-color: {rgba("secondary_container", 0.10)};
}}
QFrame#Banner[tone="error"] {{
    border: 1px solid {rgba("error", 0.45)};
    background-color: {rgba("error", 0.10)};
}}

/* ---------- Tipografía por rol -------------------------------------- */
QLabel {{
    background-color: transparent;
    color: {c["on_surface"]};
}}
QLabel[role="headline"] {{
    font-family: "{sans}";
    font-size: {FONT_SIZE["headline_lg"]}px;
    font-weight: 700;
    color: {c["on_surface"]};
}}
QLabel[role="cardTitle"] {{
    font-family: "{sans}";
    font-size: {FONT_SIZE["headline_sm"]}px;
    font-weight: 600;
    color: {c["on_surface"]};
}}
QLabel[role="brandTitle"] {{
    font-family: "{sans}";
    font-size: {FONT_SIZE["headline_sm"]}px;
    font-weight: 700;
    color: {c["primary"]};
}}
QLabel[role="subtitle"] {{
    font-family: "{sans}";
    font-size: {FONT_SIZE["body_sm"]}px;
    color: {c["on_surface_variant"]};
}}
/* Las etiquetas monoespaciadas fijan su fuente por código (QSS no soporta
   letter-spacing), así que aquí solo se define el color. */
QLabel[role="sectionLabel"], QLabel[role="fieldLabel"], QLabel[role="fieldLength"] {{
    color: {c["on_surface_variant"]};
}}
QLabel[role="cardIcon"] {{
    color: {c["primary_container"]};
    background-color: transparent;
}}
QLabel[role="mutedIcon"] {{
    color: {c["on_surface_variant"]};
    background-color: transparent;
}}
QLabel[role="errorText"] {{
    font-family: "{sans}";
    font-size: {FONT_SIZE["body_sm"]}px;
    color: {c["error"]};
}}
QLabel[role="chip"] {{
    color: {c["primary"]};
    background-color: {rgba("primary", 0.10)};
    border: 1px solid {rgba("primary", 0.24)};
    border-radius: {r["control"]}px;
    padding: 3px 8px;
}}
QLabel[role="chip"][tone="neutral"] {{
    color: {c["on_surface_variant"]};
    background-color: {c["surface_container_high"]};
    border: 1px solid {c["outline_variant"]};
}}
QLabel[role="chip"][tone="warning"] {{
    color: {c["tertiary"]};
    background-color: {rgba("tertiary", 0.12)};
    border: 1px solid {rgba("tertiary", 0.32)};
}}

/* ---------- Botones -------------------------------------------------- */
/* Por defecto: acción secundaria sobre superficie elevada.
   No se declaran «font-family» ni «font-size»: la fuente de la aplicación ya es
   la correcta y, si se fijaran aquí, ganarían al ``setFont`` de los botones
   solo-icono y sus glifos se dibujarían al tamaño del texto. */
QPushButton {{
    background-color: {c["surface_container_high"]};
    color: {c["on_surface"]};
    border: 1px solid {c["outline_variant"]};
    border-radius: {r["control"]}px;
    padding: 8px 16px;
    font-weight: 500;
    min-height: 20px;
}}
QPushButton:hover {{
    background-color: {c["surface_variant"]};
    border-color: {c["outline"]};
}}
QPushButton:pressed {{
    background-color: {c["surface_container"]};
}}
QPushButton:disabled {{
    background-color: {c["surface_container_low"]};
    color: {c["outline"]};
    border-color: {c["outline_variant"]};
}}

QPushButton[variant="primary"] {{
    background-color: {c["primary_container"]};
    color: {c["on_primary_container"]};
    border: 1px solid {c["primary_container"]};
    font-weight: 600;
}}
QPushButton[variant="primary"]:hover {{
    background-color: {c["primary_container_hover"]};
    border-color: {c["primary_container_hover"]};
}}
QPushButton[variant="primary"]:pressed {{
    background-color: {c["primary_container_pressed"]};
    border-color: {c["primary_container_pressed"]};
}}
QPushButton[variant="primary"]:disabled {{
    background-color: {c["surface_container_high"]};
    color: {c["outline"]};
    border-color: {c["outline_variant"]};
}}

QPushButton[variant="ghost"] {{
    background-color: transparent;
    color: {c["on_surface_variant"]};
    border: 1px solid {c["outline_variant"]};
}}
QPushButton[variant="ghost"][compact="true"] {{
    padding: 4px 3px;
}}
QPushButton[variant="ghost"]:hover {{
    background-color: {c["surface_variant"]};
    color: {c["on_surface"]};
}}
QPushButton[variant="ghost"]:pressed {{
    background-color: {c["surface_container"]};
}}

QPushButton[variant="danger"] {{
    background-color: transparent;
    color: {c["error"]};
    border: 1px solid {rgba("error", 0.40)};
}}
QPushButton[variant="danger"]:hover {{
    background-color: {rgba("error", 0.12)};
    border-color: {c["error"]};
}}

QPushButton[variant="link"] {{
    background-color: transparent;
    color: {c["primary"]};
    border: none;
    padding: 4px 6px;
    font-weight: 500;
}}
QPushButton[variant="link"]:hover {{
    color: {c["primary_fixed"]};
    background-color: transparent;
}}

/* Botones de navegación de la barra lateral. */
QPushButton[variant="nav"] {{
    background-color: transparent;
    color: {c["on_surface_variant"]};
    border: none;
    border-radius: {r["control"]}px;
    padding: 8px 10px;
    text-align: left;
    font-weight: 500;
}}
QPushButton[variant="nav"]:hover {{
    background-color: {c["surface_container_high"]};
    color: {c["on_surface"]};
}}
QPushButton[variant="nav"]:checked {{
    background-color: {c["secondary_container"]};
    color: {c["on_secondary_container"]};
    font-weight: 600;
}}
QPushButton[variant="nav"][tone="danger"] {{
    color: {c["error"]};
}}
QPushButton[variant="nav"][tone="danger"]:hover {{
    background-color: {rgba("error", 0.12)};
    color: {c["error"]};
}}

/* Botón cuadrado solo-icono. */
QPushButton[variant="icon"] {{
    background-color: transparent;
    color: {c["on_surface_variant"]};
    border: none;
    border-radius: {r["pill"]}px;
    padding: 0;
    min-width: 32px;
    max-width: 32px;
    min-height: 32px;
    max-height: 32px;
}}
QPushButton[variant="icon"]:hover {{
    background-color: {c["surface_container_high"]};
    color: {c["primary"]};
}}
QPushButton[variant="icon"]:pressed {{
    background-color: {c["surface_variant"]};
}}

/* Botones de la barra flotante sobre el visor. */
QPushButton[variant="hud"] {{
    background-color: transparent;
    color: {c["primary"]};
    border: none;
    border-radius: {r["pill"]}px;
    padding: 0;
    min-width: 30px;
    max-width: 30px;
    min-height: 30px;
    max-height: 30px;
}}
QPushButton[variant="hud"]:hover {{
    background-color: {rgba("primary_container", 0.22)};
}}
QPushButton[variant="hud"]:pressed {{
    background-color: {rgba("primary_container", 0.35)};
}}
QPushButton[variant="hud"]:checked {{
    background-color: {c["primary_container"]};
    color: {c["on_primary_container"]};
}}
QPushButton[variant="hud"]:disabled {{
    background-color: transparent;
    color: {c["outline_variant"]};
}}

/* ---------- Campos de entrada --------------------------------------- */
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox,
QDateEdit, QTimeEdit {{
    background-color: {c["surface_dim"]};
    color: {c["on_surface"]};
    border: 1px solid {c["outline_variant"]};
    border-radius: {r["control"]}px;
    padding: 6px 8px;
    font-family: "{sans}";
    font-size: {FONT_SIZE["body_md"]}px;
    min-height: 20px;
    selection-background-color: {c["primary_container"]};
    selection-color: {c["on_primary_container"]};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus,
QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus, QTimeEdit:focus {{
    border: 1px solid {c["primary_container"]};
    background-color: {c["surface_container_lowest"]};
}}
QLineEdit:hover, QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover,
QDateEdit:hover, QTimeEdit:hover {{
    border-color: {c["outline"]};
}}
QLineEdit:disabled, QTextEdit:disabled, QComboBox:disabled, QSpinBox:disabled,
QDoubleSpinBox:disabled {{
    background-color: {c["surface_container_low"]};
    color: {c["outline"]};
    border-color: {c["outline_variant"]};
}}
/* Solo lectura: se lee como dato calculado, no como campo editable. */
QLineEdit[readOnly="true"] {{
    background-color: {c["surface_container_low"]};
    color: {c["on_surface_variant"]};
    border: 1px solid {c["outline_variant"]};
}}
QLineEdit[readOnly="true"]:focus {{
    border: 1px solid {c["outline_variant"]};
    background-color: {c["surface_container_low"]};
}}
/* Datos técnicos (CP, RFC, teléfonos, medidas) en monoespaciada. */
QLineEdit[role="mono"], QSpinBox[role="mono"], QDoubleSpinBox[role="mono"] {{
    font-family: "{mono}";
    font-size: {FONT_SIZE["body_sm"]}px;
}}
QLineEdit[state="error"], QComboBox[state="error"], QTextEdit[state="error"] {{
    border: 1px solid {c["error"]};
}}

QComboBox QAbstractItemView {{
    background-color: {c["surface_container_high"]};
    color: {c["on_surface"]};
    border: 1px solid {c["outline_variant"]};
    border-radius: {r["control"]}px;
    padding: 4px;
    outline: none;
    selection-background-color: {c["primary_container"]};
    selection-color: {c["on_surface"]};
}}
QComboBox QAbstractItemView::item {{
    min-height: 26px;
    padding: 4px 8px;
    border-radius: {r["control"]}px;
    background-color: transparent;
    color: {c["on_surface"]};
}}
QComboBox QAbstractItemView::item:hover,
QComboBox QAbstractItemView::item:selected {{
    background-color: {c["primary_container"]};
    color: {c["on_surface"]};
}}

QCalendarWidget QWidget {{
    background-color: {c["surface_container"]};
    color: {c["on_surface"]};
}}
QCalendarWidget QAbstractItemView {{
    background-color: {c["surface_container"]};
    color: {c["on_surface"]};
    selection-background-color: {c["primary_container"]};
    selection-color: {c["on_primary_container"]};
}}

/* ---------- Listas --------------------------------------------------- */
QListWidget {{
    background-color: {c["surface_dim"]};
    color: {c["on_surface"]};
    border: 1px solid {c["outline_variant"]};
    border-radius: {r["control"]}px;
    padding: 4px;
    outline: none;
}}
QListWidget::item {{
    padding: 6px;
    border-radius: {r["control"]}px;
    color: {c["on_surface_variant"]};
}}
QListWidget::item:hover {{
    background-color: {c["surface_container_high"]};
    color: {c["on_surface"]};
}}
QListWidget::item:selected {{
    background-color: {rgba("primary_container", 0.22)};
    color: {c["primary_fixed"]};
}}
QListWidget#receiverResults::item {{
    padding: 0px;
    margin: 0px;
    background: transparent;
    border: none;
}}
QListWidget#receiverResults::item:hover,
QListWidget#receiverResults::item:selected {{
    background: transparent;
    color: {c["on_surface"]};
}}
QFrame#receiverResultCard {{
    background-color: {c["surface_container"]};
    border: 1px solid {c["outline_variant"]};
    border-radius: {r["card"]}px;
}}
QFrame#receiverResultCard:hover {{
    border: 1px solid {c["primary"]};
    background-color: {c["surface_container_high"]};
}}
QFrame#receiverAddressCount {{
    background-color: {rgba("tertiary", 0.12)};
    border: 1px solid {rgba("tertiary", 0.45)};
    border-radius: {r["control"]}px;
}}
QFrame#receiverAddressCount QLabel {{
    color: {c["tertiary"]};
    background-color: transparent;
    font-size: {FONT_SIZE["label_sm"]}px;
}}

/* ---------- Agrupadores --------------------------------------------- */
QGroupBox {{
    background-color: {c["surface_container_low"]};
    border: 1px solid {c["outline_variant"]};
    border-radius: {r["card"]}px;
    margin-top: 16px;
    padding: 12px 12px 10px 12px;
    font-family: "{mono}";
    font-size: {FONT_SIZE["label_md"]}px;
    font-weight: 500;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 0 6px;
    color: {c["primary"]};
}}

/* ---------- Selección múltiple / binaria ---------------------------- */
QCheckBox, QRadioButton {{
    color: {c["on_surface_variant"]};
    spacing: 8px;
    background-color: transparent;
}}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border: 2px solid {c["outline"]};
    background-color: {c["surface_dim"]};
}}
QCheckBox::indicator {{
    border-radius: {r["control"]}px;
}}
QRadioButton::indicator {{
    border-radius: 10px;
}}
QCheckBox::indicator:hover, QRadioButton::indicator:hover {{
    border-color: {c["primary"]};
}}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background-color: {c["primary_container"]};
    border-color: {c["primary_container"]};
}}

/* ---------- Progreso ------------------------------------------------- */
QProgressBar {{
    background-color: {c["surface_container_high"]};
    border: none;
    border-radius: 3px;
    max-height: 6px;
    min-height: 6px;
}}
QProgressBar::chunk {{
    background-color: {c["primary_container"]};
    border-radius: 3px;
}}

/* ---------- Áreas desplazables -------------------------------------- */
QScrollArea {{
    background-color: transparent;
    border: none;
}}
/* Idioma habitual de Qt para que el contenido del viewport no pinte fondo. */
QScrollArea > QWidget > QWidget {{
    background-color: transparent;
}}
QScrollBar:vertical {{
    background-color: transparent;
    width: 10px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background-color: {c["outline_variant"]};
    border-radius: 5px;
    min-height: 32px;
}}
QScrollBar::handle:vertical:hover {{
    background-color: {c["outline"]};
}}
QScrollBar:horizontal {{
    background-color: transparent;
    height: 10px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background-color: {c["outline_variant"]};
    border-radius: 5px;
    min-width: 32px;
}}
QScrollBar::handle:horizontal:hover {{
    background-color: {c["outline"]};
}}
QScrollBar::add-line, QScrollBar::sub-line {{
    height: 0;
    width: 0;
}}
QScrollBar::add-page, QScrollBar::sub-page {{
    background-color: transparent;
}}

/* ---------- Menús contextuales y tooltips --------------------------- */
QMenuBar {{
    background-color: {c["surface_container"]};
    color: {c["on_surface"]};
    border-bottom: 1px solid {c["outline_variant"]};
}}
QMenuBar::item {{
    padding: 6px 10px;
    background-color: transparent;
}}
QMenuBar::item:selected {{
    background-color: {c["surface_container_high"]};
}}
QMenu {{
    background-color: {c["surface_container_high"]};
    color: {c["on_surface"]};
    border: 1px solid {c["outline_variant"]};
    border-radius: {r["control"]}px;
    padding: 4px;
}}
QMenu::item {{
    padding: 6px 24px 6px 12px;
    border-radius: {r["control"]}px;
}}
QMenu::item:selected {{
    background-color: {c["primary_container"]};
    color: {c["on_primary_container"]};
}}
QMenu::separator {{
    height: 1px;
    background-color: {c["outline_variant"]};
    margin: 4px 8px;
}}
QToolTip {{
    background-color: {c["surface_container_highest"]};
    color: {c["on_surface"]};
    border: 1px solid {c["outline_variant"]};
    border-radius: {r["control"]}px;
    padding: 4px 8px;
}}

/* ---------- Visor de imagen ----------------------------------------- */
QGraphicsView#ImageCanvas {{
    background-color: {c["surface_container_lowest"]};
    border: 1px solid {c["outline_variant"]};
    border-radius: {r["control"]}px;
}}
/* Barra flotante de herramientas del visor. Sin desenfoque disponible en QSS,
   se usa un fondo casi opaco con borde de acento. */
#ViewerHud {{
    background-color: {rgba("surface_container", 0.94)};
    border: 1px solid {rgba("primary", 0.35)};
    border-radius: {r["pill"]}px;
}}
#ViewerHudSeparator {{
    background-color: {rgba("primary", 0.30)};
    border: none;
    max-width: 1px;
    min-width: 1px;
}}
/* Recorte OCR: relleno al 10 % y esquinas rectas para transmitir precisión
   (DESIGN.md, «OCR Bounding Boxes»). */
QRubberBand {{
    background-color: {rgba("ocr_selection_fill", 0.10)};
    border: 1px solid {c["ocr_selection"]};
}}

/* ---------- Divisores redimensionables ------------------------------ */
QSplitter::handle {{
    background-color: transparent;
}}
QSplitter::handle:horizontal {{
    width: 8px;
}}
QSplitter::handle:vertical {{
    height: 8px;
}}
QSplitter::handle:hover {{
    background-color: {rgba("primary_container", 0.25)};
}}

/* ---------- Diálogos del sistema ------------------------------------ */
QMessageBox {{
    background-color: {c["surface_container"]};
}}
QMessageBox QLabel {{
    color: {c["on_surface"]};
    font-size: {FONT_SIZE["body_md"]}px;
}}
QMessageBox QPushButton {{
    min-width: 104px;
}}

/* ---------- Tablas ---------------------------------------------------- */
QTableWidget {{
    background-color: {c["surface_container"]};
    color: {c["on_surface"]};
    border: 1px solid {c["outline_variant"]};
    border-radius: {r["control"]}px;
    padding: 4px;
    outline: none;
}}

QTabWidget QWidget {{
    background-color: {c["surface_container"]};
    color: {c["on_surface"]};
    border: 1px solid {c["outline_variant"]};
    border-radius: {r["control"]}px;
    padding: 4px;
    outline: none;
}}
QTabWidget::pane {{
  border: 1px solid {c["outline_variant"]};
  border-radius: {r["control"]}px;
  margin: 0px;
  padding: 0px;
}}
QTabWidget::pane:selected {{
  background-color: {c["surface_container_high"]};
  border: 1px solid {c["outline_variant"]};
}}

QTableWidget#ShipmentsTable QHeaderView::section {{
    background-color: {c["primary_container"]};
    color: {c["on_surface"]};
    border: none;
    border-right: 1px solid {c["outline_variant"]};
    padding: 10px 12px;
    font-weight: 600;
    font-size: {FONT_SIZE["body_lg"]}px;
}}

/* ---------- Historial de envíos -------------------------------------- */
QDialog#ShipmentsHistoryWindow {{
    background-color: {c["surface"]};
}}
QDialog#ShipmentsHistoryWindow QLabel[role="headline"] {{
    font-size: {FONT_SIZE["headline_lg"]}px;
    font-weight: 600;
    color: {c["on_surface"]};
}}
QDialog#ShipmentsHistoryWindow QDateEdit,
QDialog#ShipmentsHistoryWindow QTimeEdit,
QDialog#ShipmentsHistoryWindow QComboBox#shipmentsScopeCombo {{
    background-color: {c["surface_container_high"]};
    color: {c["on_surface"]};
    border: 1px solid {c["outline_variant"]};
    border-radius: {r["control"]}px;
    padding: 6px 10px;
    min-height: 22px;
    font-size: {FONT_SIZE["body_sm"]}px;
}}
QDialog#ShipmentsHistoryWindow QDateEdit,
QDialog#ShipmentsHistoryWindow QTimeEdit {{
    font-family: "{mono}";
}}
QDialog#ShipmentsHistoryWindow QDateEdit:focus,
QDialog#ShipmentsHistoryWindow QTimeEdit:focus,
QDialog#ShipmentsHistoryWindow QComboBox#shipmentsScopeCombo:focus {{
    border: 1px solid {c["primary_container"]};
}}
QDialog#ShipmentsHistoryWindow QComboBox#shipmentsScopeCombo {{
    padding-right: 28px;
    min-width: 176px;
}}
QDialog#ShipmentsHistoryWindow QComboBox#shipmentsScopeCombo QAbstractItemView {{
    background-color: {c["surface_container_high"]};
    color: {c["on_surface"]};
    border: 1px solid {c["outline_variant"]};
    padding: 4px;
    outline: none;
    selection-background-color: {c["primary_container"]};
    selection-color: {c["on_surface"]};
}}
QDialog#ShipmentsHistoryWindow QComboBox#shipmentsScopeCombo QAbstractItemView::item {{
    min-height: 28px;
    padding: 6px 10px;
    background-color: transparent;
    color: {c["on_surface"]};
}}
QDialog#ShipmentsHistoryWindow QComboBox#shipmentsScopeCombo QAbstractItemView::item:hover,
QDialog#ShipmentsHistoryWindow QComboBox#shipmentsScopeCombo QAbstractItemView::item:selected {{
    background-color: {c["primary_container"]};
    color: {c["on_surface"]};
}}
QFrame#ShipmentsTableCard {{
    background-color: {c["surface_container_lowest"]};
    border: 1px solid {c["outline_variant"]};
    border-radius: {r["card"]}px;
}}
QTableWidget#ShipmentsTable {{
    background-color: transparent;
    alternate-background-color: {c["surface_container_low"]};
    color: {c["on_surface"]};
    border: none;
    border-radius: 0px;
    padding: 0px;
    gridline-color: transparent;
    selection-background-color: {rgba("primary_container", 0.22)};
    selection-color: {c["on_surface"]};
    font-size: {FONT_SIZE["body_sm"]}px;
}}
QTableWidget#ShipmentsTable::item {{
    padding: 8px 12px;
    border-bottom: 1px solid {rgba("outline_variant", 0.45)};
}}
QTableWidget#ShipmentsTable::item:hover {{
    background-color: {c["surface_container_low"]};
}}
QTableWidget#ShipmentsTable QHeaderView::section {{
    background-color: {c["surface"]};
    color: {c["on_surface_variant"]};
    border: none;
    border-bottom: 1px solid {c["outline_variant"]};
    border-right: 1px solid {rgba("outline_variant", 0.35)};
    padding: 10px 12px;
    font-family: "{mono}";
    font-size: {FONT_SIZE["label_sm"]}px;
    font-weight: 700;
}}
QTableWidget#ShipmentsTable QScrollBar:horizontal,
QTableWidget#ShipmentsTable QScrollBar:vertical {{
    background: transparent;
    border: none;
    margin: 0px;
}}
QTableWidget#ShipmentsTable QScrollBar:horizontal {{
    height: 8px;
}}
QTableWidget#ShipmentsTable QScrollBar:vertical {{
    width: 8px;
}}
QTableWidget#ShipmentsTable QScrollBar::handle:horizontal,
QTableWidget#ShipmentsTable QScrollBar::handle:vertical {{
    background: {c["surface_container_highest"]};
    border-radius: 4px;
    min-width: 24px;
    min-height: 24px;
}}
QTableWidget#ShipmentsTable QScrollBar::handle:horizontal:hover,
QTableWidget#ShipmentsTable QScrollBar::handle:vertical:hover {{
    background: {c["outline_variant"]};
}}
QTableWidget#ShipmentsTable QScrollBar::add-line,
QTableWidget#ShipmentsTable QScrollBar::sub-line,
QTableWidget#ShipmentsTable QScrollBar::add-page,
QTableWidget#ShipmentsTable QScrollBar::sub-page {{
    background: transparent;
    border: none;
    width: 0px;
    height: 0px;
}}
QFrame#ShipmentsTableFooter {{
    background-color: {c["surface_container"]};
    border-top: 1px solid {c["outline_variant"]};
}}
QLabel#ShipmentsPageLabel {{
    color: {c["on_surface_variant"]};
    font-size: {FONT_SIZE["body_sm"]}px;
}}
QDialog#ShipmentsHistoryWindow QPushButton#shipmentsPrevButton,
QDialog#ShipmentsHistoryWindow QPushButton#shipmentsNextButton {{
    min-width: 96px;
    border: 1px solid {c["outline_variant"]};
    border-radius: {r["control"]}px;
    padding: 4px 12px;
}}
QDialog#ShipmentsHistoryWindow QPushButton#shipmentsPrevButton:disabled,
QDialog#ShipmentsHistoryWindow QPushButton#shipmentsNextButton:disabled {{
    color: {c["outline"]};
    border-color: {rgba("outline_variant", 0.5)};
}}
QDialog#ShipmentsHistoryWindow QPushButton#shipmentsCancelButton,
QDialog#ShipmentsHistoryWindow QPushButton#shipmentsExportFooterButton,
QDialog#ShipmentsHistoryWindow QPushButton#shipmentsExportButton,
QDialog#ShipmentsHistoryWindow QPushButton#shipmentsConsultButton {{
    min-height: 38px;
}}


/* ---------- Login ---------------------------------------------------- */
#LoginCard {{
    background-color: {c["surface_container"]};
    border: 1px solid {c["outline_variant"]};
    border-radius: {r["card"]}px;
}}
#LoginLogo {{
    background-color: {c["surface_container_high"]};
    border: 1px solid {c["outline_variant"]};
    border-radius: {r["card"]}px;
    color: {c["primary"]};
}}
#LoginErrorBanner {{
    background-color: {rgba("error", 0.10)};
    border: 1px solid {rgba("error", 0.45)};
    border-radius: {r["control"]}px;
}}
#LoginFooter {{
    color: {c["outline"]};
    font-size: {FONT_SIZE["label_sm"]}px;
}}

/* ---------- Ventana de envíos: densidad alta ------------------------ */
/* Muchos campos en pantalla: se recorta el alto de los controles sin perder
   legibilidad (ver DESIGN.md, «Data Density»). */
QDialog#ShipmentWindow QLineEdit,
QDialog#ShipmentWindow QTextEdit,
QDialog#ShipmentWindow QComboBox,
QDialog#ShipmentWindow QSpinBox,
QDialog#ShipmentWindow QDoubleSpinBox {{
    padding: 4px 8px;
    min-height: 18px;
}}
QDialog#ShipmentWindow QTextEdit {{
    min-height: 64px;
}}
QDialog#ShipmentWindow QPushButton[variant="primary"],
QDialog#ShipmentWindow QPushButton[variant="ghost"] {{
    min-width: 150px;
}}

/* ---------- Subcontroles dibujados con imagen ----------------------- */
{_subcontrols_qss()}
"""
