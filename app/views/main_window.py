"""Ventana principal: shell con barra lateral, barra superior, lienzo e inspector."""

import logging
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QAction, QDesktopServices, QKeySequence, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app.components.image_viewer import ImageViewer
from app.components.navigation import Sidebar, TopBar
from app.components.panels.queue_panel import QueuePanel
from app.components.panels.right_panel import RightPanel
from app.components.panels.viewer_toolbar import ViewerToolbar
from app.components.theme import INSPECTOR_WIDTH, SPACE
from app.components.widgets import Card, chip, icon_button, subtitle, text_button
from app.config import DATA_DIR, ZOOM_FACTOR
from app.services.image_service import load_image
from app.services.paquetexpress_service import (
    PaquetexpressCoverageNotFoundError,
    PaquetexpressServiceError,
    PaquetexpressSessionExpiredError,
    get_coverages_for_postal_code,
    record_from_existing_shipment,
)
from app.services.registros_service import (
    RepositorySessionExpiredError,
    insert_extraction,
    validate_extraction,
)
from app.states.image_state import ImageStateStore
from app.states.workers.ai_worker import AIWorker
from app.utils.logs import log_directory
from app.utils.record_mapper import to_db_record
from app.views.export_dialog import ExportDialog
from app.views.export_shipments import ExportShipments
from app.views.session_relogin import prompt_relogin_after_session_expired
from app.views.shipment_window import ShipmentWindow
from app.config import IMAGES_DIR

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Shell principal de la aplicación."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Extractor OCR - Destinatarios")
        self.resize(1440, 900)
        self.setMinimumSize(1180, 720)

        # Estado
        self._current_image_path: Path | None = None
        self._current_image_np = None  # Imagen base sin recortar
        self._current_display_np = None  # Imagen mostrada (rotada)
        self._current_crop_np = None  # Recorte aplicado (para enviar a IA)
        self._ai_worker: AIWorker | None = None
        # Caché de estado por imagen (hasta que se guarde): foto, recorte, datos IA
        self._image_states = ImageStateStore()

        self._setup_ui()
        self._setup_actions()
        self._connect_signals()
        self._update_actions_enabled()
        self._refresh_topbar()

        # Asegurar directorios
        (DATA_DIR / "exports").mkdir(parents=True, exist_ok=True)

    # --- Construcción de la interfaz -----------------------------------

    def _setup_ui(self):
        central = QWidget()
        central.setObjectName("AppShell")
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_sidebar())
        root.addWidget(self._build_content_area(), 1)
        self.setCentralWidget(central)

    def _build_sidebar(self) -> Sidebar:
        self._sidebar = Sidebar()
        self._queue = QueuePanel()
        self._sidebar.set_queue_widget(self._queue)

        self._sidebar.add_nav_item("workspace", "Workspace", "document_scanner", is_section=True)
        self._sidebar.add_nav_item("export", "Exportar registros", "download")
        self._sidebar.add_nav_item("shipments", "Ver envíos", "download", is_section=True)
        self._sidebar.add_nav_item("logs", "Ver logs", "terminal")
        self._sidebar.add_nav_item("about", "Acerca de", "info", footer=True)
        self._sidebar.add_nav_item("quit", "Salir", "logout", tone="danger", footer=True)
        self._sidebar.set_active_section("workspace")
        return self._sidebar

    def _build_content_area(self) -> QWidget:
        content = QWidget()
        content.setObjectName("ContentArea")
        column = QVBoxLayout(content)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(0)

        self._topbar = TopBar()
        self._btn_topbar_export = icon_button("download", "Exportar registros (Ctrl+E)")
        self._topbar.add_action_widget(self._btn_topbar_export)
        column.addWidget(self._topbar)

        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(SPACE["md"], SPACE["md"], SPACE["md"], SPACE["md"])
        body_layout.setSpacing(0)

        self._right = RightPanel()
        self._right.setMinimumWidth(360)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._build_canvas_card())
        splitter.addWidget(self._right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        splitter.setSizes([900, INSPECTOR_WIDTH])
        body_layout.addWidget(splitter)

        column.addWidget(body, 1)
        return content

    def _build_canvas_card(self) -> Card:
        card = Card("Documento", "image")
        card.set_body_margins(SPACE["sm"], SPACE["sm"], SPACE["sm"], SPACE["sm"])
        self._canvas_chip = chip("SIN IMAGEN", tone="neutral")
        card.add_header_widget(self._canvas_chip)

        self._viewer = ImageViewer()
        self._viewer.setObjectName("ImageCanvas")
        self._hud = ViewerToolbar()
        self._hud.set_enabled_controls(False)

        # El HUD flota sobre el lienzo: el visor abarca las tres filas de la
        # rejilla y el HUD ocupa solo la del medio. Así el HUD tapa únicamente su
        # propio rectángulo y el resto del lienzo sigue recibiendo el ratón para
        # seleccionar el recorte. No se envuelve en un contenedor transparente al
        # ratón porque ese atributo también anula los clics de sus hijos.
        canvas_area = QWidget()
        grid = QGridLayout(canvas_area)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(0)
        grid.addWidget(self._viewer, 0, 0, 3, 1)
        grid.setRowMinimumHeight(0, SPACE["sm"] + 4)  # separación con el borde
        grid.addWidget(
            self._hud, 1, 0, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop
        )
        grid.setRowStretch(2, 1)
        self._hud.raise_()

        card.body.addWidget(canvas_area, 1)
        card.body.addWidget(self._build_crop_actions())
        return card

    def _build_crop_actions(self) -> QWidget:
        row_widget = QWidget()
        row = QHBoxLayout(row_widget)
        row.setContentsMargins(SPACE["xs"], 0, SPACE["xs"], 0)
        row.setSpacing(SPACE["sm"])

        self._crop_hint = subtitle(
            "Arrastra sobre la imagen para seleccionar la zona del destinatario."
        )
        row.addWidget(self._crop_hint, 1)

        self._btn_retry_crop = text_button("Reintentar recorte", variant="ghost", icon="refresh")
        row.addWidget(self._btn_retry_crop)
        self._btn_apply_crop = text_button("Aplicar recorte", variant="primary", icon="crop")
        row.addWidget(self._btn_apply_crop)
        return row_widget

    def _setup_actions(self):
        """Atajos de teclado.

        Al no haber barra de menús, las acciones se registran en la ventana para
        que los atajos históricos sigan funcionando.
        """
        self._add_shortcut(QKeySequence.StandardKey.Open, self._on_open)
        self._add_shortcut("Ctrl+E", self._on_export)
        self._add_shortcut(QKeySequence.StandardKey.Quit, QApplication.quit)
        self._add_shortcut("Ctrl++", lambda: self._viewer.scale(ZOOM_FACTOR, ZOOM_FACTOR))
        self._add_shortcut("Ctrl+-", lambda: self._viewer.scale(1 / ZOOM_FACTOR, 1 / ZOOM_FACTOR))
        self._add_shortcut("Ctrl+0", self._viewer.reset_view)
        self._add_shortcut("Ctrl+L", self._viewer.rotate_left)
        self._add_shortcut("Ctrl+R", self._viewer.rotate_right)

    def _add_shortcut(self, shortcut, slot) -> QAction:
        action = QAction(self)
        action.setShortcut(shortcut)
        action.triggered.connect(slot)
        self.addAction(action)
        return action

    def _connect_signals(self):
        self._sidebar.open_images_requested.connect(self._on_open)
        self._sidebar.nav_activated.connect(self._on_nav_activated)
        self._queue.image_activated.connect(self._on_image_activated)
        self._btn_topbar_export.clicked.connect(self._on_export)

        self._hud.zoom_in_clicked.connect(lambda: self._viewer.scale(ZOOM_FACTOR, ZOOM_FACTOR))
        self._hud.zoom_out_clicked.connect(
            lambda: self._viewer.scale(1 / ZOOM_FACTOR, 1 / ZOOM_FACTOR)
        )
        self._hud.fit_clicked.connect(self._viewer.reset_view)
        self._hud.rotate_left_clicked.connect(self._viewer.rotate_left)
        self._hud.rotate_right_clicked.connect(self._viewer.rotate_right)
        self._hud.square_mode_changed.connect(self._viewer.set_square_mode)

        self._btn_apply_crop.clicked.connect(self._on_apply_crop)
        self._btn_retry_crop.clicked.connect(self._on_retry_crop)
        self._viewer.crop_changed.connect(self._update_actions_enabled)

        self._right.sede_changed.connect(self._update_actions_enabled)
        self._right.send_to_ai_clicked.connect(self._on_send_to_ai)
        self._right.check_coverage_clicked.connect(self._on_check_coverage)
        self._right.save_clicked.connect(self._on_save)
        self._right.receiver_selected.connect(
            lambda _receiver, _address: self._update_actions_enabled()
        )
        self._right.receiver_cleared.connect(self._update_actions_enabled)
        self._right.form_changed.connect(self._update_actions_enabled)
        self._right.create_shipment_for_receiver_clicked.connect(
            self._on_create_shipment_for_receiver
        )
        self._right.edit_receiver_clicked.connect(self._on_edit_receiver)

    # --- Navegación ----------------------------------------------------

    def _on_nav_activated(self, item_id: str):
        if item_id == "export":
            self._on_export()
        elif item_id == "shipments":
            self._on_open_shipments()
        elif item_id == "logs":
            self._on_open_logs()
        elif item_id == "about":
            self._on_about()
        elif item_id == "quit":
            QApplication.quit()

    def _on_open_logs(self):
        directory = log_directory()
        if not directory.is_dir():
            QMessageBox.information(
                self,
                "Sin logs",
                f"Todavía no existe la carpeta de logs:\n{directory}",
            )
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(directory)))

    # --- Imágenes ------------------------------------------------------

    def _on_open(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Abrir imágenes",
            "",
            "Imágenes (*.jpg *.jpeg *.png *.JPG *.JPEG *.PNG);;Todos (*.*)",
        )
        if not paths:
            return
        path_list = [Path(p) for p in paths]
        self._queue.add_images(path_list)
        if not self._current_image_path and path_list:
            self._on_image_activated(path_list[0])
        self._refresh_topbar()

    def _save_current_state(self):
        """Guarda el estado de la imagen actual en el caché (antes de cambiar)."""
        if self._current_image_path is None:
            return
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
        self._image_states.save(self._current_image_path, {
            "rotation_deg": self._viewer.rotation_deg,
            "crop_rect": crop_rect,
            "form_data": form_data,
            "aspect_mode": self._hud.square_mode(),
        })

    def _on_image_activated(self, path: Path):
        # Guardar estado de la imagen actual antes de cambiar
        self._save_current_state()

        self._current_image_path = path
        self._queue.set_current_image(path)
        # El destinatario pertenece al sobre anterior: cada imagen vuelve a
        # empezar por el paso 2 del flujo.
        self._right.reset_receiver()
        img = load_image(path)
        if img is None:
            self._update_actions_enabled()
            self._refresh_topbar()
            return

        self._current_image_np = img
        self._current_display_np = img.copy()
        self._current_crop_np = None
        self._hud.set_enabled_controls(True)

        state = self._image_states.get(path)
        if state:
            # Restaurar: imagen con rotación, recorte y datos de IA
            rot = state.get("rotation_deg", 0)
            self._viewer.set_image(img, rot)
            self._hud.set_square_mode(state.get("aspect_mode", False))
            self._viewer.set_square_mode(state.get("aspect_mode", False))
            if state.get("crop_rect"):
                self._viewer.set_crop_rect(state["crop_rect"])
                self._current_crop_np = self._viewer.get_cropped_image()
            self._right.set_form_data(state.get("form_data", {}))
        else:
            self._viewer.set_image(img)
            self._right.clear_form()

        self._update_actions_enabled()
        self._refresh_topbar()

    def _refresh_topbar(self):
        name = self._current_image_path.name if self._current_image_path else None
        self._topbar.set_current_file(name)
        self._topbar.set_queue_count(self._queue.count())

    def _on_apply_crop(self):
        crop_np = self._viewer.get_cropped_image()
        if crop_np is not None:
            self._current_crop_np = crop_np
            # Mantenemos la imagen mostrada; el recorte está en _current_crop_np
            self._update_actions_enabled()
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
            self._update_actions_enabled()

    def _update_actions_enabled(self):
        """Habilita cada acción según la rama del flujo en la que esté el operador."""
        has_sede = self._right.sede() is not None
        has_crop = self._current_crop_np is not None
        has_ocr = self._right.has_ocr_data()
        has_receiver = (
            self._right.selected_receiver() is not None
            and self._right.selected_address() is not None
        )
        self._right.set_send_enabled(bool(has_sede and has_crop))
        self._right.set_create_shipment_enabled(bool(has_crop and has_receiver))
        self._right.set_coverage_enabled(has_ocr)
        self._right.set_save_enabled(has_ocr)
        self._update_canvas_status(has_crop)

    def _update_canvas_status(self, has_crop: bool):
        if self._current_image_np is None:
            self._canvas_chip.setText("SIN IMAGEN")
            tone = "neutral"
        elif has_crop:
            self._canvas_chip.setText("RECORTE APLICADO")
            tone = "primary"
        else:
            self._canvas_chip.setText("SELECCIONE ZONA")
            tone = "warning"
        self._canvas_chip.setProperty("tone", tone)
        style = self._canvas_chip.style()
        style.unpolish(self._canvas_chip)
        style.polish(self._canvas_chip)

    # --- IA ------------------------------------------------------------

    def _on_send_to_ai(self):
        if self._current_crop_np is None:
            QMessageBox.warning(self, "Sin recorte", "Aplique un recorte primero.")
            return
        sede = self._right.sede()
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
        self._update_actions_enabled()
        self._ai_worker = None

    def _on_ai_error(self, msg: str):
        self._right.set_loading(False)
        QMessageBox.critical(
            self,
            "Error de IA",
            f"Error al conectar con la API:\n{msg}\n\nRevise OPENAI_API_KEY en .env",
        )
        self._ai_worker = None

    # --- Cobertura y envíos --------------------------------------------

    def _on_create_shipment_for_receiver(self):
        """Rama con destinatario existente. Si no hubo extracción, copia el envío al registro."""
        receiver = self._right.selected_receiver()
        address = self._right.selected_address()
        if receiver is None or address is None:
            QMessageBox.warning(
                self,
                "Sin destinatario",
                "Busque al destinatario y elija uno de sus domicilios.",
            )
            return
        if self._current_crop_np is None:
            QMessageBox.warning(
                self,
                "Sin recorte",
                "Aplique el recorte del sobre: es la referencia de la pantalla de envío.",
            )
            return

        dialog = ShipmentWindow.for_receiver(
            receiver,
            address,
            self._current_crop_np,
            parent=self,
            contact=self._right.selected_contact(),
        )
        # La cobertura se consulta al abrir con el CP del domicilio; si el CP no
        # tiene cobertura, el diálogo se rechaza solo y se vuelve a Workspace.
        had_extraction = self._right.has_ocr_data()
        if dialog.exec() != QDialog.DialogCode.Accepted or had_extraction:
            return
        chosen = dialog.chosen_for_record()
        if chosen is None:
            return
        self._right.set_form_data(record_from_existing_shipment(*chosen))
        self._update_actions_enabled()

    def _on_edit_receiver(self, receiver) -> None:
        """Abre el diálogo de alta en modo edición, con el recorte del sobre."""
        from app.views.receiver_dialog import ReceiverDialog

        dialog = ReceiverDialog.for_edit(
            receiver,
            crop_np=self._current_crop_np,
            address=self._right.selected_address(),
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted or dialog.created_receiver is None:
            return
        preferred = dialog.preferred_address_id
        self._right.show_receiver(
            dialog.created_receiver,
            preferred,
            dialog.preferred_contact_id,
        )

    def _on_check_coverage(self):
        """Rama sin destinatario (paso 5b): cobertura con el código postal del OCR."""
        form_data = self._right.get_form_data()
        campos = form_data.get("campos") or {}
        postal_code = str(campos.get("codigo_postal") or "").strip()
        if not postal_code:
            QMessageBox.critical(
                self,
                "Error",
                "No se encontró código postal en los datos OCR para consultar cobertura.",
            )
            return

        try:
            coverages = get_coverages_for_postal_code(postal_code)
        except PaquetexpressCoverageNotFoundError as exc:
            QMessageBox.warning(
                self,
                "Sin cobertura",
                (
                    "No existe cobertura para el código postal consultado, así que "
                    "no se abre la creación del envío ni se da de alta al "
                    "destinatario.\n\nGuarde el registro OCR y continúe con la "
                    "siguiente imagen.\n\n"
                    f"{exc}"
                ),
            )
            return
        except PaquetexpressSessionExpiredError as exc:
            prompt_relogin_after_session_expired(
                self, f"No se pudo consultar cobertura: {exc}"
            )
            return
        except PaquetexpressServiceError as exc:
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudo consultar cobertura: {exc}",
            )
            return

        # En esta rama la referencia son los campos OCR, no el recorte: el paso
        # 7b muestra las coberturas junto al alta precargada con la extracción.
        dialog = ShipmentWindow(coverages, form_data, parent=self)
        dialog.exec()

    # --- Persistencia --------------------------------------------------

    def _on_save(self):
        form_data = self._right.get_form_data()
        sede = self._right.sede() or ""

        rect = self._viewer.get_current_crop()
        meta = {
            "sede": sede,
            "nombre_imagen": (
                self._current_image_path.name if self._current_image_path else ""
            ),
            "crop_x": rect[0] if rect else None,
            "crop_y": rect[1] if rect else None,
            "crop_w": rect[2] if rect else None,
            "crop_h": rect[3] if rect else None,
            "rotation_deg": self._viewer.rotation_deg,
            "aspect_mode": "SQUARE" if self._hud.square_mode() else "FREE",
        }
        record = to_db_record(form_data, meta)
        validation_errors = validate_extraction(record)
        if validation_errors:
            details = "\n".join(
                f"- {error['campo']}: {error['error']}"
                for error in validation_errors
            )
            QMessageBox.critical(
                self,
                "Errores de validación",
                f"Corrija los siguientes campos:\n\n{details}",
            )
            return

        assert self._current_image_path is not None
        saved_path = self._current_image_path
        try:
            insert_extraction(record)
            QMessageBox.information(self, "Guardado", "Registro guardado correctamente.")
        except RepositorySessionExpiredError as e:
            logger.warning("Sesión caducada o no autorizado al guardar")
            prompt_relogin_after_session_expired(self, f"No se pudo guardar: {e}")
            return
        except Exception as e:
            logger.exception("Error al guardar")
            QMessageBox.critical(self, "Error", f"No se pudo guardar: {e}")
            return

        # Eliminar de caché y lista; deseleccionar SEDE; pasar a la siguiente imagen
        self._image_states.remove(saved_path)
        self._right.clear_sede()
        next_path = self._queue.remove_image(saved_path)
        # Limpiar estado actual para que _save_current_state no guarde al cambiar
        self._current_image_path = None
        self._current_image_np = None
        self._current_display_np = None
        self._current_crop_np = None
        self._viewer.set_image(None)
        self._right.clear_form()
        self._right.reset_receiver()
        self._hud.set_enabled_controls(False)
        if next_path is not None:
            self._on_image_activated(next_path)
        self._update_actions_enabled()
        self._refresh_topbar()

    # --- Diálogos auxiliares -------------------------------------------

    def _on_export(self):
        dlg = ExportDialog(self)
        dlg.exec()
    
    def _on_open_shipments(self):
        dlg = ExportShipments(self)
        dlg.exec()

    def _on_about(self):
        QMessageBox.about(
            self,
            "Acerca de",
            "Extractor OCR - Destinatarios\n\n"
            "Aplicación para extraer texto de etiquetas de sobres usando visión por IA.\n"
            "Sedes: AJUSCO | COYOACÁN",
        )
