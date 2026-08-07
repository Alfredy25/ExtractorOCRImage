"""Shell de navegación: barra lateral y barra superior.

Sustituyen a los ``QDockWidget`` y al menú de la versión anterior. Los elementos
de navegación solo emiten identificadores; quién los atiende es la ventana
principal, de modo que este módulo no conoce servicios ni flujos.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.components.theme import SPACE
from app.components.widgets import (
    chip,
    divider,
    icon_label,
    nav_button,
    section_label,
    subtitle,
    text_button,
)


class Sidebar(QFrame):
    """Barra lateral: identidad, acción principal, navegación y cola de trabajo."""

    open_images_requested = Signal()
    nav_activated = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._nav_buttons: dict[str, QPushButton] = {}
        self._section_group = QButtonGroup(self)
        self._section_group.setExclusive(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACE["sm"] + 4, SPACE["md"], SPACE["sm"] + 4, SPACE["md"])
        layout.setSpacing(SPACE["sm"])

        layout.addWidget(self._build_brand())

        open_button = text_button("Abrir imágenes", variant="primary", icon="folder_open")
        open_button.setMinimumHeight(38)
        open_button.clicked.connect(self.open_images_requested.emit)
        layout.addWidget(open_button)

        layout.addSpacing(SPACE["xs"])
        self._nav_layout = QVBoxLayout()
        self._nav_layout.setSpacing(2)
        layout.addLayout(self._nav_layout)

        layout.addSpacing(SPACE["xs"])
        layout.addWidget(divider())

        self._queue_slot = QVBoxLayout()
        self._queue_slot.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(self._queue_slot, 1)

        layout.addWidget(divider())
        self._footer_layout = QVBoxLayout()
        self._footer_layout.setSpacing(2)
        layout.addLayout(self._footer_layout)

    def _build_brand(self) -> QFrame:
        brand = QFrame()
        brand.setObjectName("SidebarBrand")
        brand.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        row = QHBoxLayout(brand)
        row.setContentsMargins(SPACE["sm"] + 2, SPACE["sm"], SPACE["sm"] + 2, SPACE["sm"])
        row.setSpacing(SPACE["sm"] + 2)
        row.addWidget(icon_label("document_scanner", 24))

        text_column = QVBoxLayout()
        text_column.setSpacing(0)
        title = QLabel("Extractor OCR")
        title.setProperty("role", "brandTitle")
        text_column.addWidget(title)
        text_column.addWidget(subtitle("Terminal de captura"))
        row.addLayout(text_column, 1)
        return brand

    def add_nav_item(
        self,
        item_id: str,
        text: str,
        icon: str,
        is_section: bool = False,
        tone: str | None = None,
        footer: bool = False,
    ) -> QPushButton:
        """Añade un elemento de navegación.

        ``is_section`` marca destinos con estado «aquí estás» (mutuamente
        excluyentes); el resto son acciones que abren diálogos o ventanas.
        """
        button = nav_button(text, icon, tone=tone)
        button.setCheckable(is_section)
        if is_section:
            self._section_group.addButton(button)
        button.clicked.connect(lambda: self.nav_activated.emit(item_id))
        self._nav_buttons[item_id] = button
        target = self._footer_layout if footer else self._nav_layout
        target.addWidget(button)
        return button

    def set_active_section(self, item_id: str) -> None:
        button = self._nav_buttons.get(item_id)
        if button is not None and button.isCheckable():
            button.setChecked(True)

    def set_queue_widget(self, widget: QWidget) -> None:
        """Coloca la cola de trabajo en el hueco central de la barra."""
        self._queue_slot.addWidget(widget)


class TopBar(QFrame):
    """Barra superior: título de la vista, archivo activo y acciones rápidas."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("TopBar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(SPACE["lg"], SPACE["sm"], SPACE["lg"], SPACE["sm"])
        layout.setSpacing(SPACE["md"])

        title_column = QVBoxLayout()
        title_column.setSpacing(0)
        self._title = QLabel("Captura de destinatarios")
        self._title.setProperty("role", "cardTitle")
        title_column.addWidget(self._title)
        self._breadcrumb = subtitle("Recorta la zona del destinatario y envíala a la IA")
        title_column.addWidget(self._breadcrumb)
        layout.addLayout(title_column)

        layout.addStretch(1)

        self._file_label = section_label("Sin imagen")
        layout.addWidget(self._file_label)
        self._queue_chip = chip("0 en cola", tone="neutral")
        layout.addWidget(self._queue_chip)

        self._actions_layout = QHBoxLayout()
        self._actions_layout.setSpacing(SPACE["xs"])
        layout.addLayout(self._actions_layout)

    def add_action_widget(self, widget: QWidget) -> None:
        self._actions_layout.addWidget(widget)

    def set_current_file(self, name: str | None) -> None:
        self._file_label.setText((name or "Sin imagen").upper())

    def set_queue_count(self, count: int) -> None:
        label = "1 en cola" if count == 1 else f"{count} en cola"
        self._queue_chip.setText(label)

    def set_subtitle(self, text: str) -> None:
        self._breadcrumb.setText(text)
