"""Panel izquierdo: lista de imágenes, sede, controles de recorte."""
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QButtonGroup,
    QRadioButton,
    QGroupBox,
    QHBoxLayout,
    QFileDialog,
    QLabel,
    QCheckBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from app.core.image_io import load_image, np_to_qpixmap
from app.config import SEDES


class LeftPanel(QWidget):
    """Panel con lista de imágenes, selector de sede y botones de recorte."""

    open_images_requested = Signal()
    images_selected = Signal(list)  # list[Path]
    image_activated = Signal(Path)
    sede_changed = Signal(str)  # AJUSCO | COYOACÁN
    rotate_left_clicked = Signal()
    rotate_right_clicked = Signal()
    square_mode_changed = Signal(bool)
    apply_crop_clicked = Signal()
    retry_crop_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._images: list[Path] = []
        self._sede: str | None = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Botón abrir
        btn_open = QPushButton("Abrir imágenes…")
        btn_open.clicked.connect(self._on_open)
        layout.addWidget(btn_open)

        # Lista con miniaturas
        self._list = QListWidget()
        self._list.setIconSize(self._list.iconSize() * 2)
        self._list.itemDoubleClicked.connect(self._on_item_activated)
        layout.addWidget(QLabel("Cola de trabajo:"))
        layout.addWidget(self._list)

        # Sede
        gb_sede = QGroupBox("SEDE")
        sede_layout = QVBoxLayout(gb_sede)
        self._sede_group = QButtonGroup()
        for sede in SEDES:
            rb = QRadioButton(sede)
            rb.toggled.connect(lambda checked, s=sede: self._on_sede_toggled(checked, s))
            self._sede_group.addButton(rb)
            sede_layout.addWidget(rb)
        layout.addWidget(gb_sede)

        # Rotación
        rot_layout = QHBoxLayout()
        btn_rot_l = QPushButton("Rotar 90° Izq.")
        btn_rot_r = QPushButton("Rotar 90° Der.")
        btn_rot_l.clicked.connect(self.rotate_left_clicked.emit)
        btn_rot_r.clicked.connect(self.rotate_right_clicked.emit)
        rot_layout.addWidget(btn_rot_l)
        rot_layout.addWidget(btn_rot_r)
        layout.addLayout(rot_layout)

        # Modo recorte
        self._square_check = QCheckBox("Recorte cuadrado (1:1)")
        self._square_check.toggled.connect(self.square_mode_changed.emit)
        layout.addWidget(self._square_check)

        # Aplicar / Reintentar
        btn_apply = QPushButton("Aplicar recorte")
        btn_retry = QPushButton("Reintentar recorte")
        btn_apply.clicked.connect(self.apply_crop_clicked.emit)
        btn_retry.clicked.connect(self.retry_crop_clicked.emit)
        layout.addWidget(btn_apply)
        layout.addWidget(btn_retry)

        layout.addStretch()

    def _on_open(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Abrir imágenes",
            "",
            "Imágenes (*.jpg *.jpeg *.png *.JPG *.JPEG *.PNG);;Todos (*.*)",
        )
        if paths:
            self._images = [Path(p) for p in paths]
            self._populate_list()
            self.images_selected.emit(self._images)

    def _populate_list(self):
        self._list.clear()
        for p in self._images:
            item = QListWidgetItem(p.name)
            img = load_image(p)
            if img is not None:
                pix = np_to_qpixmap(img)
                thumb = pix.scaled(64, 64, aspectMode=Qt.AspectRatioMode.KeepAspectRatio)
                item.setIcon(QIcon(thumb))
            item.setData(256, str(p))
            self._list.addItem(item)

    def _on_item_activated(self, item: QListWidgetItem):
        path_str = item.data(256)
        if path_str:
            self.image_activated.emit(Path(path_str))

    def _on_sede_toggled(self, checked: bool, sede: str):
        if checked:
            self._sede = sede
            self.sede_changed.emit(sede)

    def set_images(self, paths: list[Path]):
        self._images = paths
        self._populate_list()

    def add_images(self, paths: list[Path]):
        for p in paths:
            if p not in self._images:
                self._images.append(p)
        self._populate_list()

    def current_image_path(self) -> Path | None:
        item = self._list.currentItem()
        if item is None:
            return None
        path_str = item.data(256)
        return Path(path_str) if path_str else None

    def set_current_image(self, path: Path):
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item and item.data(256) == str(path):
                self._list.setCurrentRow(i)
                return

    def remove_image(self, path: Path) -> Path | None:
        """
        Elimina la imagen de la lista. Retorna la siguiente imagen a mostrar
        (la que estaba después, o la primera si era la última, o None si queda vacía).
        """
        try:
            idx = self._images.index(path)
        except ValueError:
            return None
        self._images.pop(idx)
        self._populate_list()
        if not self._images:
            return None
        next_idx = min(idx, len(self._images) - 1)
        return self._images[next_idx]

    def get_images(self) -> list[Path]:
        return list(self._images)

    def sede(self) -> str | None:
        return self._sede

    def square_mode(self) -> bool:
        return self._square_check.isChecked()

    def set_square_mode(self, checked: bool):
        self._square_check.setChecked(checked)

    def clear_sede(self):
        """Deselecciona la SEDE para dejar limpio tras guardar."""
        self._sede_group.setExclusive(False)
        for rb in self._sede_group.buttons():
            rb.setChecked(False)
        self._sede_group.setExclusive(True)
        self._sede = None
