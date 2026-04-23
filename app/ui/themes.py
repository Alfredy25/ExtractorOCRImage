"""Temas visuales: modo cálido y modo oscuro (paletas design tokens)."""
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSettings

# --- Modo cálido (referencia: fondo crema, tarjetas suaves, acentos azul claro) ---
PALETTE_WARM = {
    "primary_100": "#d4eaf7",
    "primary_200": "#b6ccd8",
    "primary_300": "#3b3c3d",
    "accent_100": "#71c4ef",
    "accent_200": "#00668c",
    "text_100": "#1d1c1c",
    "text_200": "#313d44",
    "bg_100": "#fffefb",
    # Fondo principal del área de trabajo (sólido, como la referencia)
    "bg_main": "#f5f4f1",
    "bg_200": "#f5f4f1",
    "bg_300": "#cccbc8",
    # Degradado horizontal tipo tarjeta: izq. azul muy claro → der. #b6ccd8 (línea x:0→1; equiv. RTL x:1→0)
    "grad_surface_0": "#f0f8fc",
    "grad_surface_1": "#d4eaf7",
    "grad_surface_2": "#b6ccd8",
    # Bordes suaves (evita aspecto “negro” en modo claro)
    "border_soft": "#e6e4e0",
    "border_mist": "#d8ecf5",
    # Degradados botón (tonos claros → acento; sin bordes oscuros)
    "grad_btn_0": "#f5fbfe",
    "grad_btn_1": "#d4eaf7",
    "grad_btn_2": "#9fd4f0",
    "grad_btn_hover_0": "#d4eaf7",
    "grad_btn_hover_1": "#8ecfef",
    "grad_btn_pressed": "#c5dce8",
}

# --- Modo oscuro (referencia: dashboard alto contraste, azul #0085ff) ---
PALETTE_DARK = {
    "primary_100": "#0085ff",
    "primary_200": "#69b4ff",
    "primary_300": "#e0ffff",
    "accent_100": "#006fff",
    "accent_200": "#e1ffff",
    "text_100": "#FFFFFF",
    "text_200": "#9e9e9e",
    "bg_100": "#1E1E1E",
    "bg_200": "#2d2d2d",
    "bg_300": "#454545",
}

R_MAIN = "12px"
R_CTRL = "10px"
R_INPUT = "8px"


def _theme_dark() -> str:
    p = PALETTE_DARK
    return f"""
    QMainWindow, QWidget {{
        background-color: {p["bg_100"]};
    }}
    QDockWidget {{
        background-color: {p["bg_200"]};
        color: {p["text_100"]};
        titlebar-close-icon: none;
        titlebar-normal-icon: none;
        font-weight: 500;
    }}
    QDockWidget::title {{
        background-color: {p["bg_200"]};
        color: {p["primary_200"]};
        padding: 8px 12px;
        font-size: 13px;
    }}
    QGroupBox {{
        background-color: {p["bg_200"]};
        color: {p["text_100"]};
        border: 1px solid {p["bg_300"]};
        border-radius: {R_MAIN};
        margin-top: 12px;
        padding: 12px 12px 8px 12px;
        font-weight: 500;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 12px;
        padding: 0 6px;
        color: {p["primary_200"]};
    }}
    QPushButton {{
        background-color: {p["primary_100"]};
        color: {p["text_100"]};
        border: 1px solid {p["accent_100"]};
        border-radius: {R_CTRL};
        padding: 10px 16px;
        font-weight: 600;
    }}
    QPushButton:hover {{
        background-color: {p["primary_200"]};
        border-color: {p["primary_100"]};
    }}
    QPushButton:pressed {{
        background-color: {p["accent_100"]};
    }}
    QPushButton:disabled {{
        background-color: {p["bg_300"]};
        color: {p["text_200"]};
        border-color: {p["bg_300"]};
    }}
    QLineEdit, QTextEdit, QPlainTextEdit {{
        background-color: {p["bg_200"]};
        color: {p["text_100"]};
        border: 1px solid {p["bg_300"]};
        border-radius: {R_INPUT};
        padding: 8px 12px;
        selection-background-color: {p["accent_100"]};
    }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
        border-color: {p["primary_100"]};
    }}
    QLineEdit::placeholder, QTextEdit::placeholder, QPlainTextEdit::placeholder {{
        color: {p["text_200"]};
    }}
    QLabel {{
        color: {p["text_200"]};
    }}
    QListWidget {{
        background-color: {p["bg_200"]};
        color: {p["text_100"]};
        border: 1px solid {p["bg_300"]};
        border-radius: {R_MAIN};
        padding: 6px;
        outline: none;
    }}
    QListWidget::item {{
        padding: 8px;
        border-radius: 8px;
    }}
    QListWidget::item:selected {{
        background-color: {p["primary_100"]};
        color: {p["text_100"]};
    }}
    QListWidget::item:hover {{
        background-color: {p["bg_300"]};
    }}
    QRadioButton {{
        color: {p["text_200"]};
        spacing: 8px;
    }}
    QRadioButton::indicator {{
        width: 18px;
        height: 18px;
        border-radius: 9px;
        border: 2px solid {p["primary_200"]};
        background-color: {p["bg_200"]};
    }}
    QRadioButton::indicator:checked {{
        background-color: {p["primary_100"]};
        border-color: {p["primary_300"]};
    }}
    QCheckBox {{
        color: {p["text_200"]};
        spacing: 8px;
    }}
    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border-radius: 4px;
        border: 2px solid {p["primary_200"]};
        background-color: {p["bg_200"]};
    }}
    QCheckBox::indicator:checked {{
        background-color: {p["primary_100"]};
        border-color: {p["accent_100"]};
    }}
    QScrollArea {{
        background-color: transparent;
        border: none;
    }}
    QScrollBar:vertical {{
        background-color: {p["bg_200"]};
        width: 12px;
        border-radius: 6px;
        margin: 2px;
    }}
    QScrollBar::handle:vertical {{
        background-color: {p["bg_300"]};
        border-radius: 6px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background-color: {p["primary_200"]};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    QProgressBar {{
        background-color: {p["bg_200"]};
        border-radius: {R_INPUT};
        text-align: center;
        color: {p["text_100"]};
    }}
    QProgressBar::chunk {{
        background-color: {p["primary_100"]};
        border-radius: {R_INPUT};
    }}
    QMenuBar {{
        background-color: {p["bg_200"]};
        color: {p["text_100"]};
    }}
    QMenuBar::item:selected {{
        background-color: {p["bg_300"]};
        color: {p["primary_300"]};
    }}
    QMenu {{
        background-color: {p["bg_200"]};
        color: {p["text_100"]};
        border: 1px solid {p["bg_300"]};
    }}
    QMenu::item:selected {{
        background-color: {p["bg_300"]};
    }}
    QComboBox {{
        background-color: {p["bg_200"]};
        color: {p["text_100"]};
        border: 1px solid {p["bg_300"]};
        border-radius: {R_INPUT};
        padding: 8px 12px;
    }}
    QComboBox:hover {{
        border-color: {p["primary_100"]};
    }}
    QComboBox::drop-down {{
        border: none;
    }}
    QComboBox QAbstractItemView {{
        background-color: {p["bg_200"]};
        color: {p["text_100"]};
        selection-background-color: {p["bg_300"]};
        selection-color: {p["text_100"]};
        outline: none;
    }}
    QComboBox QAbstractItemView::item {{
        min-height: 22px;
        padding: 4px 8px;
    }}
    QDateEdit {{
        background-color: {p["bg_200"]};
        color: {p["text_100"]};
        border: 1px solid {p["bg_300"]};
        border-radius: {R_INPUT};
        padding: 8px;
    }}
    QTimeEdit {{
        background-color: {p["bg_200"]};
        color: {p["text_100"]};
        border: 1px solid {p["bg_300"]};
        border-radius: {R_INPUT};
        padding: 8px;
    }}
    QCalendarWidget QWidget {{
        background-color: {p["bg_200"]};
        color: {p["text_100"]};
    }}
    QGraphicsView {{
        background-color: {p["bg_100"]};
    }}
    QRubberBand {{
        background-color: rgba(0, 133, 255, 0.35);
        border: 2px solid {p["primary_200"]};
    }}
    QDialog {{
        background-color: {p["bg_200"]};
        color: {p["text_100"]};
    }}
    QMessageBox {{
        background-color: {p["bg_200"]};
        color: {p["text_100"]};
    }}
"""


def _theme_warm() -> str:
    w = PALETTE_WARM
    return f"""
    QMainWindow, QWidget {{
        background-color: {w["bg_main"]};
    }}
    QDockWidget {{
        background-color: {w["bg_main"]};
        color: {w["text_100"]};
        titlebar-close-icon: none;
        titlebar-normal-icon: none;
        font-weight: 500;
        border: none;
    }}
    QDockWidget::title {{
        background-color: transparent;
        color: {w["text_200"]};
        padding: 8px 12px;
        font-size: 13px;
        font-weight: 600;
    }}
    QGroupBox {{
        /* Degradado horizontal: derecha #b6ccd8 ← izquierda azul clarito (vector x 1→0 = RTL) */
        background: qlineargradient(x1:1, y1:0, x2:0, y2:0,
            stop:0 {w["grad_surface_2"]},
            stop:0.55 {w["grad_surface_1"]},
            stop:1 {w["grad_surface_0"]});
        color: {w["text_100"]};
        border: none;
        border-radius: {R_MAIN};
        margin-top: 12px;
        padding: 12px 12px 8px 12px;
        font-weight: 600;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 12px;
        padding: 0 6px;
        color: {w["text_200"]};
    }}
    QPushButton {{
        color: {w["text_100"]};
        border: 1px solid {w["border_mist"]};
        border-radius: {R_CTRL};
        padding: 10px 16px;
        font-weight: 600;
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 {w["grad_btn_0"]},
            stop:0.5 {w["grad_btn_1"]},
            stop:1 {w["grad_btn_2"]});
    }}
    QPushButton:hover {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 {w["grad_btn_hover_0"]},
            stop:1 {w["grad_btn_hover_1"]});
        border: 1px solid {w["accent_100"]};
        color: {w["text_100"]};
    }}
    QPushButton:pressed {{
        background: {w["grad_btn_pressed"]};
        border: 1px solid {w["primary_200"]};
        color: {w["text_100"]};
    }}
    QPushButton:disabled {{
        background: {w["bg_main"]};
        color: {w["text_200"]};
        border: 1px solid {w["border_soft"]};
    }}
    QLineEdit, QTextEdit, QPlainTextEdit {{
        background-color: {w["bg_100"]};
        color: {w["text_100"]};
        border: 1px solid {w["border_soft"]};
        border-radius: {R_INPUT};
        padding: 8px 12px;
        selection-background-color: {w["primary_100"]};
    }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
        border: 1px solid {w["border_mist"]};
    }}
    QLineEdit::placeholder, QTextEdit::placeholder, QPlainTextEdit::placeholder {{
        color: {w["text_200"]};
    }}
    QLabel {{
        color: {w["text_100"]};
    }}
    QListWidget {{
        background-color: {w["bg_main"]};
        color: {w["text_100"]};
        border: 1px solid {w["border_soft"]};
        border-radius: {R_MAIN};
        padding: 6px;
        outline: none;
    }}
    QListWidget::item {{
        padding: 8px;
        border-radius: 8px;
    }}
    QListWidget::item:selected {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 {w["primary_100"]},
            stop:1 {w["accent_100"]});
        color: {w["text_100"]};
    }}
    QListWidget::item:hover {{
        background-color: rgba(212, 234, 247, 0.65);
    }}
    QRadioButton {{
        color: {w["text_100"]};
        spacing: 8px;
    }}
    QRadioButton::indicator {{
        width: 18px;
        height: 18px;
        border-radius: 9px;
        border: 2px solid {w["border_mist"]};
        background-color: {w["bg_100"]};
    }}
    QRadioButton::indicator:checked {{
        background-color: {w["accent_100"]};
        border: 2px solid {w["accent_100"]};
    }}
    QCheckBox {{
        color: {w["text_100"]};
        spacing: 8px;
    }}
    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border-radius: 4px;
        border: 2px solid {w["border_mist"]};
        background-color: {w["bg_100"]};
    }}
    QCheckBox::indicator:checked {{
        background-color: {w["accent_100"]};
        border: 2px solid {w["accent_100"]};
    }}
    QScrollArea {{
        background-color: transparent;
        border: none;
    }}
    QScrollBar:vertical {{
        background-color: {w["bg_main"]};
        width: 12px;
        border-radius: 6px;
        margin: 2px;
    }}
    QScrollBar::handle:vertical {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 {w["primary_200"]},
            stop:1 {w["accent_100"]});
        border-radius: 6px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background-color: {w["accent_100"]};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    QProgressBar {{
        background-color: {w["bg_main"]};
        border: 1px solid {w["border_soft"]};
        border-radius: {R_INPUT};
        text-align: center;
        color: {w["text_100"]};
    }}
    QProgressBar::chunk {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 {w["accent_100"]},
            stop:1 {w["primary_100"]});
        border-radius: {R_INPUT};
    }}
    QMenuBar {{
        background-color: {w["bg_main"]};
        color: {w["text_100"]};
    }}
    QMenuBar::item:selected {{
        background-color: {w["primary_100"]};
        color: {w["text_100"]};
    }}
    QMenu {{
        background-color: {w["bg_100"]};
        color: {w["text_100"]};
        border: 1px solid {w["border_soft"]};
    }}
    QMenu::item:selected {{
        background-color: {w["primary_100"]};
    }}
    QComboBox {{
        background-color: {w["bg_100"]};
        color: {w["text_100"]};
        border: 1px solid {w["border_soft"]};
        border-radius: {R_INPUT};
        padding: 8px 12px;
    }}
    QComboBox:hover {{
        border: 1px solid {w["border_mist"]};
    }}
    QComboBox::drop-down {{
        border: none;
    }}
    QDateEdit {{
        background-color: {w["bg_100"]};
        color: {w["text_100"]};
        border: 1px solid {w["border_soft"]};
        border-radius: {R_INPUT};
        padding: 8px;
    }}
    QTimeEdit {{
        background-color: {w["bg_100"]};
        color: {w["text_100"]};
        border: 1px solid {w["border_soft"]};
        border-radius: {R_INPUT};
        padding: 8px;
    }}
    QCalendarWidget QWidget {{
        background-color: {w["bg_100"]};
        color: {w["text_100"]};
    }}
    QGraphicsView {{
        background-color: {w["bg_main"]};
    }}
    QRubberBand {{
        background-color: rgba(113, 196, 239, 0.35);
        border: 2px solid {w["accent_100"]};
    }}
    QDialog {{
        background-color: {w["bg_main"]};
        color: {w["text_100"]};
    }}
    QMessageBox {{
        background-color: {w["bg_main"]};
        color: {w["text_100"]};
    }}
"""


THEMES = {"dark": _theme_dark(), "warm": _theme_warm()}
THEME_NAMES = {"dark": "Modo oscuro", "warm": "Modo cálido"}


def get_saved_theme() -> str:
    """Obtiene el tema guardado (persistido con QSettings)."""
    s = QSettings("ExtractorOCR", "ExtractorOCR")
    return s.value("theme", "dark", type=str)


def save_theme(theme: str) -> None:
    """Guarda la preferencia de tema."""
    s = QSettings("ExtractorOCR", "ExtractorOCR")
    s.setValue("theme", theme)


def apply_theme(theme: str) -> None:
    """Aplica el tema a la aplicación."""
    qss = THEMES.get(theme, THEMES["dark"])
    app = QApplication.instance()
    if app:
        app.setStyleSheet(qss)
