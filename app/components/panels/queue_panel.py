"""Cola de trabajo: miniaturas de las imágenes pendientes de procesar.

Vive dentro de la barra lateral. Solo gestiona la lista; abrir el diálogo de
archivos es responsabilidad de la ventana principal.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.components.theme import SPACE
from app.components.widgets import chip, section_label
from app.utils.image_io import load_image, np_to_qpixmap

_PATH_ROLE = Qt.ItemDataRole.UserRole
_THUMB_SIZE = 44


class QueuePanel(QWidget):
    """Lista de imágenes en cola, con miniatura y nombre de archivo."""

    image_activated = Signal(Path)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._images: list[Path] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACE["sm"])

        header = QHBoxLayout()
        header.setContentsMargins(2, 0, 2, 0)
        header.addWidget(section_label("Cola de trabajo"))
        header.addStretch(1)
        self._count_chip = chip("0", tone="neutral")
        header.addWidget(self._count_chip)
        layout.addLayout(header)

        self._list = QListWidget()
        self._list.setIconSize(QSize(_THUMB_SIZE, _THUMB_SIZE))
        self._list.setSpacing(2)
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self._list.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self._list, 1)

    # --- Eventos internos ---------------------------------------------

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        path_str = item.data(_PATH_ROLE)
        if path_str:
            self.image_activated.emit(Path(path_str))

    def _make_item(self, path: Path) -> QListWidgetItem:
        item = QListWidgetItem(path.name)
        item.setData(_PATH_ROLE, str(path))
        item.setToolTip(str(path))
        image = load_image(path)
        if image is not None:
            thumb = np_to_qpixmap(image).scaled(
                _THUMB_SIZE,
                _THUMB_SIZE,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            item.setIcon(QIcon(thumb))
        return item

    def _populate_list(self) -> None:
        self._list.clear()
        for path in self._images:
            self._list.addItem(self._make_item(path))
        self._refresh_count()

    def _refresh_count(self) -> None:
        self._count_chip.setText(str(len(self._images)))

    # --- API pública ---------------------------------------------------

    def set_images(self, paths: list[Path]) -> None:
        self._images = list(paths)
        self._populate_list()

    def add_images(self, paths: list[Path]) -> None:
        for path in paths:
            if path not in self._images:
                self._images.append(path)
        self._populate_list()

    def get_images(self) -> list[Path]:
        return list(self._images)

    def count(self) -> int:
        return len(self._images)

    def current_image_path(self) -> Path | None:
        item = self._list.currentItem()
        if item is None:
            return None
        path_str = item.data(_PATH_ROLE)
        return Path(path_str) if path_str else None

    def set_current_image(self, path: Path) -> None:
        for row in range(self._list.count()):
            item = self._list.item(row)
            if item is not None and item.data(_PATH_ROLE) == str(path):
                self._list.setCurrentRow(row)
                return

    def remove_image(self, path: Path) -> Path | None:
        """Quita la imagen y devuelve la siguiente que debe mostrarse.

        Devuelve la que ocupaba la posición siguiente (o la última si se quitó
        el final) y ``None`` si la cola queda vacía. Solo elimina esa fila: no
        repuebla la lista para no releer todas las miniaturas al guardar.
        """
        try:
            index = self._images.index(path)
        except ValueError:
            return None
        self._list.takeItem(index)
        self._images.pop(index)
        self._refresh_count()
        if not self._images:
            return None
        return self._images[min(index, len(self._images) - 1)]
