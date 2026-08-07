"""Barra flotante de herramientas del visor (zoom, ajuste, rotación, recorte 1:1).

Se superpone al lienzo, como el HUD del diseño de referencia. Solo emite
señales: la manipulación de la imagen la hace el visor.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QWidget

from app.components.widgets import icon_button, vertical_divider


class ViewerToolbar(QFrame):
    """Controles de visualización superpuestos al visor de imagen."""

    zoom_in_clicked = Signal()
    zoom_out_clicked = Signal()
    fit_clicked = Signal()
    rotate_left_clicked = Signal()
    rotate_right_clicked = Signal()
    square_mode_changed = Signal(bool)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("ViewerHud")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(2)

        self._btn_zoom_out = icon_button("zoom_out", "Alejar (Ctrl+-)", variant="hud")
        self._btn_zoom_out.clicked.connect(self.zoom_out_clicked.emit)
        layout.addWidget(self._btn_zoom_out)

        self._btn_zoom_in = icon_button("zoom_in", "Acercar (Ctrl++)", variant="hud")
        self._btn_zoom_in.clicked.connect(self.zoom_in_clicked.emit)
        layout.addWidget(self._btn_zoom_in)

        self._btn_fit = icon_button("fit_screen", "Ajustar a la ventana (Ctrl+0)", variant="hud")
        self._btn_fit.clicked.connect(self.fit_clicked.emit)
        layout.addWidget(self._btn_fit)

        layout.addWidget(vertical_divider())

        self._btn_rotate_left = icon_button("rotate_left", "Rotar 90° a la izquierda (Ctrl+L)", variant="hud")
        self._btn_rotate_left.clicked.connect(self.rotate_left_clicked.emit)
        layout.addWidget(self._btn_rotate_left)

        self._btn_rotate_right = icon_button("rotate_right", "Rotar 90° a la derecha (Ctrl+R)", variant="hud")
        self._btn_rotate_right.clicked.connect(self.rotate_right_clicked.emit)
        layout.addWidget(self._btn_rotate_right)

        layout.addWidget(vertical_divider())

        self._btn_square = icon_button(
            "aspect_ratio",
            "Recorte cuadrado 1:1",
            variant="hud",
            checkable=True,
        )
        self._btn_square.toggled.connect(self.square_mode_changed.emit)
        layout.addWidget(self._btn_square)

    def square_mode(self) -> bool:
        return self._btn_square.isChecked()

    def set_square_mode(self, checked: bool) -> None:
        self._btn_square.setChecked(checked)

    def set_enabled_controls(self, enabled: bool) -> None:
        """Habilita o deshabilita todos los controles (sin imagen cargada)."""
        for button in (
            self._btn_zoom_out,
            self._btn_zoom_in,
            self._btn_fit,
            self._btn_rotate_left,
            self._btn_rotate_right,
            self._btn_square,
        ):
            button.setEnabled(enabled)
