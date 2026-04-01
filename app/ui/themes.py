"""Temas visuales usando la paleta de colores."""
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSettings

# Paleta: #1F3A5F, #4d648d, #acc2ef, #3D5A80, #cee8ff, #0F1C2E, #1f2b3e, #374357, #FFFFFF, #e0e0e0
PALETTE = {
    "dark_blue": "#1F3A5F",
    "medium_blue": "#4d648d",
    "light_blue": "#acc2ef",
    "blue_gray": "#3D5A80",
    "pale_blue": "#cee8ff",
    "navy": "#0F1C2E",
    "dark_slate": "#1f2b3e",
    "slate": "#374357",
    "white": "#FFFFFF",
    "light_gray": "#e0e0e0",
}

THEME_DARK = f"""
    QMainWindow, QWidget {{
        background-color: {PALETTE["navy"]};
    }}
    QDockWidget {{
        background-color: {PALETTE["dark_slate"]};
        color: {PALETTE["white"]};
        titlebar-close-icon: none;
        titlebar-normal-icon: none;
        font-weight: 500;
    }}
    QDockWidget::title {{
        background-color: {PALETTE["dark_slate"]};
        color: {PALETTE["pale_blue"]};
        padding: 8px 12px;
        font-size: 13px;
    }}
    QGroupBox {{
        background-color: {PALETTE["slate"]};
        color: {PALETTE["white"]};
        border: 1px solid {PALETTE["blue_gray"]};
        border-radius: 8px;
        margin-top: 12px;
        padding: 12px 12px 8px 12px;
        font-weight: 500;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 12px;
        padding: 0 6px;
        color: {PALETTE["pale_blue"]};
    }}
    QPushButton {{
        background-color: {PALETTE["blue_gray"]};
        color: {PALETTE["white"]};
        border: 1px solid {PALETTE["medium_blue"]};
        border-radius: 8px;
        padding: 10px 16px;
        font-weight: 500;
    }}
    QPushButton:hover {{
        background-color: {PALETTE["medium_blue"]};
        border-color: {PALETTE["light_blue"]};
    }}
    QPushButton:pressed {{
        background-color: {PALETTE["dark_blue"]};
    }}
    QPushButton:disabled {{
        background-color: {PALETTE["slate"]};
        color: {PALETTE["light_gray"]};
        border-color: {PALETTE["blue_gray"]};
    }}
    QLineEdit, QTextEdit, QPlainTextEdit {{
        background-color: {PALETTE["slate"]};
        color: {PALETTE["pale_blue"]};
        border: 1px solid {PALETTE["blue_gray"]};
        border-radius: 6px;
        padding: 8px 12px;
        selection-background-color: {PALETTE["medium_blue"]};
    }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
        border-color: {PALETTE["light_blue"]};
    }}
    QLineEdit::placeholder, QTextEdit::placeholder, QPlainTextEdit::placeholder {{
        color: {PALETTE["medium_blue"]};
    }}
    QLabel {{
        color: {PALETTE["light_gray"]};
    }}
    QListWidget {{
        background-color: {PALETTE["slate"]};
        color: {PALETTE["white"]};
        border: 1px solid {PALETTE["blue_gray"]};
        border-radius: 8px;
        padding: 6px;
        outline: none;
    }}
    QListWidget::item {{
        padding: 8px;
        border-radius: 6px;
    }}
    QListWidget::item:selected {{
        background-color: {PALETTE["blue_gray"]};
        color: {PALETTE["white"]};
    }}
    QListWidget::item:hover {{
        background-color: {PALETTE["medium_blue"]};
    }}
    QRadioButton {{
        color: {PALETTE["light_gray"]};
        spacing: 8px;
    }}
    QRadioButton::indicator {{
        width: 18px;
        height: 18px;
        border-radius: 9px;
        border: 2px solid {PALETTE["medium_blue"]};
        background-color: {PALETTE["slate"]};
    }}
    QRadioButton::indicator:checked {{
        background-color: {PALETTE["medium_blue"]};
        border-color: {PALETTE["light_blue"]};
    }}
    QCheckBox {{
        color: {PALETTE["light_gray"]};
        spacing: 8px;
    }}
    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border-radius: 4px;
        border: 2px solid {PALETTE["medium_blue"]};
        background-color: {PALETTE["slate"]};
    }}
    QCheckBox::indicator:checked {{
        background-color: {PALETTE["medium_blue"]};
        border-color: {PALETTE["light_blue"]};
    }}
    QScrollArea {{
        background-color: transparent;
        border: none;
    }}
    QScrollBar:vertical {{
        background-color: {PALETTE["slate"]};
        width: 12px;
        border-radius: 6px;
        margin: 2px;
    }}
    QScrollBar::handle:vertical {{
        background-color: {PALETTE["medium_blue"]};
        border-radius: 6px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background-color: {PALETTE["light_blue"]};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    QProgressBar {{
        background-color: {PALETTE["slate"]};
        border-radius: 6px;
        text-align: center;
        color: {PALETTE["white"]};
    }}
    QProgressBar::chunk {{
        background-color: {PALETTE["medium_blue"]};
        border-radius: 6px;
    }}
    QMenuBar {{
        background-color: {PALETTE["dark_slate"]};
        color: {PALETTE["white"]};
    }}
    QMenuBar::item:selected {{
        background-color: {PALETTE["blue_gray"]};
        color: {PALETTE["pale_blue"]};
    }}
    QMenu {{
        background-color: {PALETTE["dark_slate"]};
        color: {PALETTE["white"]};
        border: 1px solid {PALETTE["blue_gray"]};
    }}
    QMenu::item:selected {{
        background-color: {PALETTE["blue_gray"]};
    }}
    QComboBox {{
        background-color: {PALETTE["slate"]};
        color: {PALETTE["white"]};
        border: 1px solid {PALETTE["blue_gray"]};
        border-radius: 6px;
        padding: 8px 12px;
    }}
    QComboBox:hover {{
        border-color: {PALETTE["medium_blue"]};
    }}
    QComboBox::drop-down {{
        border: none;
    }}
    QDateEdit {{
        background-color: {PALETTE["slate"]};
        color: {PALETTE["white"]};
        border: 1px solid {PALETTE["blue_gray"]};
        border-radius: 6px;
        padding: 8px;
    }}
    QCalendarWidget QWidget {{
        background-color: {PALETTE["dark_slate"]};
        color: {PALETTE["white"]};
    }}
    QGraphicsView {{
        background-color: {PALETTE["navy"]};
    }}
    QRubberBand {{
        background-color: rgba(77, 100, 141, 0.5);
        border: 2px solid {PALETTE["light_blue"]};
    }}
    QDialog {{
        background-color: {PALETTE["dark_slate"]};
        color: {PALETTE["white"]};
    }}
    QMessageBox {{
        background-color: {PALETTE["dark_slate"]};
        color: {PALETTE["white"]};
    }}
"""


THEME_WARM = f"""
    QMainWindow, QWidget {{
        background-color: {PALETTE["light_blue"]};
    }}
    QDockWidget {{
        background-color: {PALETTE["light_blue"]};
        color: {PALETTE["navy"]};
    }}
    QDockWidget::title {{
        background-color: {PALETTE["light_blue"]};
        color: {PALETTE["dark_blue"]};
        padding: 8px 12px;
        font-size: 13px;
        font-weight: 600;
    }}
    QGroupBox {{
        background-color: {PALETTE["white"]};
        color: {PALETTE["navy"]};
        border: 1px solid {PALETTE["light_blue"]};
        border-radius: 8px;
        margin-top: 12px;
        padding: 12px 12px 8px 12px;
        font-weight: 600;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 12px;
        padding: 0 6px;
        color: {PALETTE["dark_blue"]};
    }}
    QPushButton {{
        background-color: {PALETTE["white"]};
        color: {PALETTE["dark_blue"]};
        border: 1px solid {PALETTE["medium_blue"]};
        border-radius: 8px;
        padding: 10px 16px;
        font-weight: 500;
    }}
    QPushButton:hover {{
        background-color: {PALETTE["light_blue"]};
        border-color: {PALETTE["blue_gray"]};
        color: {PALETTE["navy"]};
    }}
    QPushButton:pressed {{
        background-color: {PALETTE["medium_blue"]};
        color: {PALETTE["white"]};
    }}
    QPushButton:disabled {{
        background-color: {PALETTE["light_gray"]};
        color: {PALETTE["slate"]};
        border-color: {PALETTE["light_blue"]};
    }}
    QLineEdit, QTextEdit, QPlainTextEdit {{
        background-color: {PALETTE["white"]};
        color: {PALETTE["navy"]};
        border: 1px solid {PALETTE["light_blue"]};
        border-radius: 6px;
        padding: 8px 12px;
        selection-background-color: {PALETTE["light_blue"]};
    }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
        border-color: {PALETTE["blue_gray"]};
    }}
    QLineEdit::placeholder, QTextEdit::placeholder, QPlainTextEdit::placeholder {{
        color: {PALETTE["medium_blue"]};
    }}
    QLabel {{
        color: {PALETTE["navy"]};
    }}
    QListWidget {{
        background-color: {PALETTE["white"]};
        color: {PALETTE["navy"]};
        border: 1px solid {PALETTE["light_blue"]};
        border-radius: 8px;
        padding: 6px;
        outline: none;
    }}
    QListWidget::item {{
        padding: 8px;
        border-radius: 6px;
    }}
    QListWidget::item:selected {{
        background-color: {PALETTE["light_blue"]};
        color: {PALETTE["navy"]};
    }}
    QListWidget::item:hover {{
        background-color: {PALETTE["pale_blue"]};
    }}
    QRadioButton {{
        color: {PALETTE["navy"]};
        spacing: 8px;
    }}
    QRadioButton::indicator {{
        width: 18px;
        height: 18px;
        border-radius: 9px;
        border: 2px solid {PALETTE["medium_blue"]};
        background-color: {PALETTE["white"]};
    }}
    QRadioButton::indicator:checked {{
        background-color: {PALETTE["medium_blue"]};
        border-color: {PALETTE["dark_blue"]};
    }}
    QCheckBox {{
        color: {PALETTE["navy"]};
        spacing: 8px;
    }}
    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border-radius: 4px;
        border: 2px solid {PALETTE["medium_blue"]};
        background-color: {PALETTE["white"]};
    }}
    QCheckBox::indicator:checked {{
        background-color: {PALETTE["medium_blue"]};
        border-color: {PALETTE["dark_blue"]};
    }}
    QScrollArea {{
        background-color: transparent;
        border: none;
    }}
    QScrollBar:vertical {{
        background-color: {PALETTE["light_blue"]};
        width: 12px;
        border-radius: 6px;
        margin: 2px;
    }}
    QScrollBar::handle:vertical {{
        background-color: {PALETTE["medium_blue"]};
        border-radius: 6px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background-color: {PALETTE["blue_gray"]};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    QProgressBar {{
        background-color: {PALETTE["light_blue"]};
        border-radius: 6px;
        text-align: center;
        color: {PALETTE["navy"]};
    }}
    QProgressBar::chunk {{
        background-color: {PALETTE["medium_blue"]};
        border-radius: 6px;
    }}
    QMenuBar {{
        background-color: {PALETTE["light_blue"]};
        color: {PALETTE["navy"]};
    }}
    QMenuBar::item:selected {{
        background-color: {PALETTE["pale_blue"]};
        color: {PALETTE["dark_blue"]};
    }}
    QMenu {{
        background-color: {PALETTE["white"]};
        color: {PALETTE["navy"]};
        border: 1px solid {PALETTE["light_blue"]};
    }}
    QMenu::item:selected {{
        background-color: {PALETTE["pale_blue"]};
    }}
    QComboBox {{
        background-color: {PALETTE["white"]};
        color: {PALETTE["navy"]};
        border: 1px solid {PALETTE["light_blue"]};
        border-radius: 6px;
        padding: 8px 12px;
    }}
    QComboBox:hover {{
        border-color: {PALETTE["medium_blue"]};
    }}
    QComboBox::drop-down {{
        border: none;
    }}
    QDateEdit {{
        background-color: {PALETTE["white"]};
        color: {PALETTE["navy"]};
        border: 1px solid {PALETTE["light_blue"]};
        border-radius: 6px;
        padding: 8px;
    }}
    QCalendarWidget QWidget {{
        background-color: {PALETTE["white"]};
        color: {PALETTE["navy"]};
    }}
    QGraphicsView {{
        background-color: {PALETTE["light_gray"]};
    }}
    QRubberBand {{
        background-color: rgba(77, 100, 141, 0.4);
        border: 2px solid {PALETTE["blue_gray"]};
    }}
    QDialog {{
        background-color: {PALETTE["white"]};
        color: {PALETTE["navy"]};
    }}
    QMessageBox {{
        background-color: {PALETTE["white"]};
        color: {PALETTE["navy"]};
    }}
"""


THEMES = {"dark": THEME_DARK, "warm": THEME_WARM}
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
    qss = THEMES.get(theme, THEME_DARK)
    app = QApplication.instance()
    if app:
        app.setStyleSheet(qss)
