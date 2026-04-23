"""Ventana principal de la aplicación."""
import logging
from pathlib import Path

from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtGui import QAction, QActionGroup, QKeySequence
from PySide6.QtWidgets import (
    QMainWindow,
    QSplitter,
    QDockWidget,
    QWidget,
    QVBoxLayout,
    QMessageBox,
    QFileDialog,
    QApplication,
)

from app.config import DATA_DIR, EXPORT_DIR
from app.core.image_io import load_image
from app.core.crop_tools import apply_crop
from app.core.ai_client import extract_fields
from app.core.repository import insert_extraction
from app.ui.image_viewer import ImageViewer
from app.ui.panels.left_panel import LeftPanel
from app.ui.panels.right_panel import RightPanel, FIELD_KEYS
from app.ui.panels.export_dialog import ExportDialog
from app.ui.themes import apply_theme, save_theme, get_saved_theme, THEME_NAMES

logger = logging.getLogger(__name__)


def _to_db_record(form_data: dict, meta: dict) -> dict:
    """Construye el record para insert_extraction (claves alineadas con columnas SQLite)."""
    campos = form_data.get("campos", {})
    record = {
        "sede": meta.get("sede", ""),
        "nombre_imagen": meta.get("nombre_imagen", ""),
        "destinatario_raw": form_data.get("destinatario_raw", "") or "",
        "observaciones_ia": form_data.get("observaciones_ia"),
        "crop_x": meta.get("crop_x"),
        "crop_y": meta.get("crop_y"),
        "crop_w": meta.get("crop_w"),
        "crop_h": meta.get("crop_h"),
        "rotation_deg": meta.get("rotation_deg"),
        "aspect_mode": meta.get("aspect_mode", "FREE"),
    }
    for k in FIELD_KEYS:
        record[k] = campos.get(k, "")
    return record


class AIWorker(QThread):
    """Worker para llamada a IA en background."""

    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, image_np, sede: str):
        super().__init__()
        self._image = image_np
        self._sede = sede

    def run(self):
        try:
            result = extract_fields(self._image, self._sede)
            self.finished.emit(result)
        except Exception as e:
            logger.exception("Error en llamada IA")
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    """Ventana principal con paneles y visor."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Extractor OCR - Destinatarios")
        self.resize(1200, 800)

        # Estado
        self._current_image_path: Path | None = None
        self._current_image_np = None  # Imagen base sin recortar
        self._current_display_np = None  # Imagen mostrada (rotada)
        self._current_crop_np = None  # Recorte aplicado (para enviar a IA)
        self._ai_worker: AIWorker | None = None
        # Caché de estado por imagen (hasta que se guarde): foto, recorte, datos IA
        self._image_states: dict[str, dict] = {}

        self._setup_ui()
        self._setup_menus()
        self._connect_signals()
        self._update_send_enabled()

        # Asegurar directorios
        (DATA_DIR / "exports").mkdir(parents=True, exist_ok=True)

    def _setup_ui(self):
        # Panel izquierdo
        self._left = LeftPanel()
        dock_left = QDockWidget("Imágenes y controles")
        dock_left.setWidget(self._left)

        # Centro: visor
        self._viewer = ImageViewer()

        # Panel derecho
        self._right = RightPanel()
        dock_right = QDockWidget("Extracción y edición")
        dock_right.setWidget(self._right)

        self.setCentralWidget(self._viewer)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock_left)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock_right)

    def _setup_menus(self):
        menubar = self.menuBar()

        # Archivo
        file_menu = menubar.addMenu("Archivo")
        act_open = QAction("Abrir…", self)
        act_open.setShortcut(QKeySequence.StandardKey.Open)
        act_open.triggered.connect(self._on_open)
        file_menu.addAction(act_open)
        act_export = QAction("Exportar…", self)
        act_export.setShortcut("Ctrl+E")
        act_export.triggered.connect(self._on_export)
        file_menu.addAction(act_export)
        file_menu.addSeparator()
        act_exit = QAction("Salir", self)
        act_exit.setShortcut(QKeySequence.StandardKey.Quit)
        act_exit.triggered.connect(QApplication.quit)
        file_menu.addAction(act_exit)

        # Ver
        view_menu = menubar.addMenu("Ver")
        theme_grp = QActionGroup(self)
        theme_grp.setExclusive(True)
        self._theme_actions = {}
        for theme_id, theme_label in THEME_NAMES.items():
            act = QAction(theme_label, self)
            act.setCheckable(True)
            act.setChecked(get_saved_theme() == theme_id)
            act.triggered.connect(lambda checked, t=theme_id: self._on_theme_changed(t))
            theme_grp.addAction(act)
            self._theme_actions[theme_id] = act
            view_menu.addAction(act)
        view_menu.addSeparator()
        act_fit = QAction("Ajustar a ventana", self)
        act_fit.triggered.connect(self._viewer.reset_view)
        view_menu.addAction(act_fit)
        act_zoom_in = QAction("Zoom +", self)
        act_zoom_in.setShortcut("Ctrl++")
        act_zoom_in.triggered.connect(lambda: self._viewer.scale(1.25, 1.25))
        view_menu.addAction(act_zoom_in)
        act_zoom_out = QAction("Zoom −", self)
        act_zoom_out.setShortcut("Ctrl+-")
        act_zoom_out.triggered.connect(lambda: self._viewer.scale(0.8, 0.8))
        view_menu.addAction(act_zoom_out)
        act_reset_zoom = QAction("Restablecer zoom", self)
        act_reset_zoom.setShortcut("Ctrl+0")
        act_reset_zoom.triggered.connect(self._viewer.reset_view)
        view_menu.addAction(act_reset_zoom)

        # Edición
        edit_menu = menubar.addMenu("Edición")
        act_rot_l = QAction("Rotar 90° Izq.", self)
        act_rot_l.setShortcut("Ctrl+L")
        act_rot_l.triggered.connect(self._viewer.rotate_left)
        edit_menu.addAction(act_rot_l)
        act_rot_r = QAction("Rotar 90° Der.", self)
        act_rot_r.setShortcut("Ctrl+R")
        act_rot_r.triggered.connect(self._viewer.rotate_right)
        edit_menu.addAction(act_rot_r)

        # Ayuda
        help_menu = menubar.addMenu("Ayuda")
        act_about = QAction("Acerca de", self)
        act_about.triggered.connect(self._on_about)
        help_menu.addAction(act_about)

    def _connect_signals(self):
        self._left.open_images_requested.connect(self._on_open)
        self._left.images_selected.connect(self._on_images_selected)
        self._left.image_activated.connect(self._on_image_activated)
        self._left.sede_changed.connect(self._on_sede_changed)
        self._left.rotate_left_clicked.connect(self._viewer.rotate_left)
        self._left.rotate_right_clicked.connect(self._viewer.rotate_right)
        self._left.square_mode_changed.connect(self._viewer.set_square_mode)
        self._left.apply_crop_clicked.connect(self._on_apply_crop)
        self._left.retry_crop_clicked.connect(self._on_retry_crop)

        self._viewer.crop_changed.connect(self._update_send_enabled)

        self._right.send_to_ai_clicked.connect(self._on_send_to_ai)
        self._right.save_clicked.connect(self._on_save)

    def _on_open(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Abrir imágenes",
            "",
            "Imágenes (*.jpg *.jpeg *.png *.JPG *.JPEG *.PNG);;Todos (*.*)",
        )
        if paths:
            path_list = [Path(p) for p in paths]
            self._left.add_images(path_list)
            if not self._current_image_path and path_list:
                self._on_image_activated(path_list[0])

    def _on_images_selected(self, paths: list):
        if paths and not self._current_image_path:
            self._on_image_activated(paths[0])

    def _save_current_state(self):
        """Guarda el estado de la imagen actual en el caché (antes de cambiar)."""
        if self._current_image_path is None:
            return
        key = str(self._current_image_path)
        crop_rect = self._viewer.get_current_crop()
        form_data = self._right.get_form_data()
        # Solo guardar si hay algo que recuperar (datos IA, recorte o rotación)
        has_data = (
            any(form_data.get("campos", {}).values())
            or form_data.get("destinatario_raw")
            or form_data.get("observaciones_ia")
            or crop_rect is not None
            or self._viewer.rotation_deg != 0
        )
        if not has_data:
            return
        self._image_states[key] = {
            "rotation_deg": self._viewer.rotation_deg,
            "crop_rect": crop_rect,
            "form_data": form_data,
            "aspect_mode": self._left.square_mode(),
        }

    def _on_image_activated(self, path: Path):
        # Guardar estado de la imagen actual antes de cambiar
        self._save_current_state()

        self._current_image_path = path
        self._left.set_current_image(path)
        img = load_image(path)
        if img is None:
            self._update_send_enabled()
            return

        self._current_image_np = img
        self._current_display_np = img.copy()
        self._current_crop_np = None

        state = self._image_states.get(str(path))
        if state:
            # Restaurar: imagen con rotación, recorte y datos de IA
            rot = state.get("rotation_deg", 0)
            self._viewer.set_image(img, rot)
            self._left.set_square_mode(state.get("aspect_mode", False))
            self._viewer.set_square_mode(state.get("aspect_mode", False))
            if state.get("crop_rect"):
                self._viewer.set_crop_rect(state["crop_rect"])
                self._current_crop_np = self._viewer.get_cropped_image()
            self._right.set_form_data(state.get("form_data", {}))
        else:
            self._viewer.set_image(img)
            self._right.clear_form()

        self._update_send_enabled()

    def _on_theme_changed(self, theme_id: str):
        apply_theme(theme_id)
        save_theme(theme_id)

    def _on_sede_changed(self, sede: str):
        self._update_send_enabled()

    def _on_apply_crop(self):
        crop_np = self._viewer.get_cropped_image()
        if crop_np is not None:
            self._current_crop_np = crop_np
            # Mantenemos la imagen mostrada; el recorte está en _current_crop_np
            self._update_send_enabled()
        else:
            QMessageBox.warning(
                self,
                "Sin selección",
                "Seleccione una región con el ratón antes de aplicar recorte.",
            )

    def _on_retry_crop(self):
        """Vuelve al estado anterior al recorte (permite seleccionar de nuevo)."""
        if self._current_image_np is not None:
            self._current_crop_np = None
            self._viewer.clear_selection()
            self._update_send_enabled()

    def _update_send_enabled(self):
        has_sede = self._left.sede() is not None
        has_crop = self._current_crop_np is not None
        self._right.set_send_enabled(bool(has_sede and has_crop))

    def _on_send_to_ai(self):
        if self._current_crop_np is None:
            QMessageBox.warning(self, "Sin recorte", "Aplique un recorte primero.")
            return
        sede = self._left.sede()
        if not sede:
            QMessageBox.warning(self, "Sin SEDE", "Seleccione una SEDE.")
            return

        self._right.set_loading(True)
        self._ai_worker = AIWorker(self._current_crop_np, sede)
        self._ai_worker.finished.connect(self._on_ai_finished)
        self._ai_worker.error.connect(self._on_ai_error)
        self._ai_worker.start()

    def _on_ai_finished(self, result: dict):
        self._right.set_loading(False)
        self._right.set_result(result)
        self._ai_worker = None

    def _on_ai_error(self, msg: str):
        self._right.set_loading(False)
        QMessageBox.critical(
            self,
            "Error de IA",
            f"Error al conectar con la API:\n{msg}\n\nRevise OPENAI_API_KEY en .env",
        )
        self._ai_worker = None

    def _on_save(self):
        form_data = self._right.get_form_data()
        sede = self._left.sede()
        if not sede:
            QMessageBox.warning(self, "Sin SEDE", "Seleccione una SEDE.")
            return
        if not self._current_image_path:
            QMessageBox.warning(self, "Sin imagen", "No hay imagen seleccionada.")
            return

        rect = self._viewer.get_current_crop()
        meta = {
            "sede": sede,
            "nombre_imagen": self._current_image_path.name,
            "crop_x": rect[0] if rect else None,
            "crop_y": rect[1] if rect else None,
            "crop_w": rect[2] if rect else None,
            "crop_h": rect[3] if rect else None,
            "rotation_deg": self._viewer.rotation_deg,
            "aspect_mode": "SQUARE" if self._left.square_mode() else "FREE",
        }
        record = _to_db_record(form_data, meta)
        saved_path = self._current_image_path
        try:
            insert_extraction(record)
            QMessageBox.information(self, "Guardado", "Registro guardado correctamente.")
        except Exception as e:
            logger.exception("Error al guardar")
            QMessageBox.critical(self, "Error", f"No se pudo guardar: {e}")
            return

        # Eliminar de caché y lista; deseleccionar SEDE; pasar a la siguiente imagen
        self._image_states.pop(str(saved_path), None)
        self._left.clear_sede()
        next_path = self._left.remove_image(saved_path)
        # Limpiar estado actual para que _save_current_state no guarde al cambiar
        self._current_image_path = None
        self._current_image_np = None
        self._current_display_np = None
        self._current_crop_np = None
        self._viewer.set_image(None)
        self._right.clear_form()
        if next_path is not None:
            self._on_image_activated(next_path)
        self._update_send_enabled()

    def _on_export(self):
        dlg = ExportDialog(self)
        dlg.exec()

    def _on_about(self):
        QMessageBox.about(
            self,
            "Acerca de",
            "Extractor OCR - Destinatarios\n\n"
            "Aplicación para extraer texto de etiquetas de sobres usando visión por IA.\n"
            "Sedes: AJUSCO | COYOACÁN",
        )
