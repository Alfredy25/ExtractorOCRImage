"""Visor de imágenes con zoom, pan, selección rectangular y rotación."""
from PySide6.QtCore import QPointF, Qt, Signal, QEvent, QRect
from PySide6.QtGui import QPainter, QPen, QColor, QWheelEvent, QMouseEvent
from PySide6.QtWidgets import (
    QGraphicsView,
    QGraphicsScene,
    QGraphicsPixmapItem,
    QRubberBand,
    QApplication,
)

import numpy as np

from app.core.image_io import np_to_qpixmap
from app.core.crop_tools import apply_rotation
from app.config import ZOOM_FACTOR


class ImageViewer(QGraphicsView):
    """Visor con zoom, pan y selección rectangular/cuadrada."""

    crop_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self._pix_item: QGraphicsPixmapItem | None = None
        self._image_np: np.ndarray | None = None  # Imagen original (sin rotación)
        self._display_np: np.ndarray | None = None  # Imagen mostrada (con rotación)
        self._rotation_deg = 0
        self._square_mode = False
        self._rubber_band: QRubberBand | None = None
        self._origin = QPointF()
        self._rubber_origin_view = None  # QPoint
        self._panning = False
        self._space_pressed = False  # Espacio mantenido para pan
        self._pan_start = QPointF()
        self._last_zoom = 1.0
        self._last_valid_rect = QRect()  # Última selección válida (para no perderla en clic)

        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        self.viewport().installEventFilter(self)

    def set_image(self, image_np: np.ndarray | None, rotation_deg: int = 0):
        """Establece la imagen a mostrar (BGR numpy). Opcionalmente con rotación previa."""
        self._image_np = image_np.copy() if image_np is not None else None
        self._rotation_deg = rotation_deg
        self._refresh_display()
        self._clear_selection()

    def _refresh_display(self):
        """Actualiza la imagen mostrada según rotación."""
        if self._image_np is None:
            self._display_np = None
            self._scene.clear()
            self._pix_item = None
            return
        self._display_np = apply_rotation(self._image_np, self._rotation_deg)
        pix = np_to_qpixmap(self._display_np)
        self._scene.clear()
        self._pix_item = self._scene.addPixmap(pix)
        self._scene.setSceneRect(self._scene.itemsBoundingRect())
        self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self._last_zoom = 1.0

    def rotate_left(self):
        """Rota -90° (anti-horario)."""
        if self._image_np is None:
            return
        self._rotation_deg = (self._rotation_deg - 90) % 360
        self._refresh_display()
        self._clear_selection()
        self.crop_changed.emit()

    def rotate_right(self):
        """Rota +90° (horario)."""
        if self._image_np is None:
            return
        self._rotation_deg = (self._rotation_deg + 90) % 360
        self._refresh_display()
        self._clear_selection()
        self.crop_changed.emit()

    def set_rotation_deg(self, deg: int):
        """Establece la rotación directamente (0, 90, 180, 270)."""
        if self._image_np is None:
            return
        self._rotation_deg = deg % 360
        self._refresh_display()
        self.crop_changed.emit()

    def set_square_mode(self, square: bool):
        """Activa/desactiva modo recorte cuadrado 1:1."""
        self._square_mode = square
        self._clear_selection()
        self.crop_changed.emit()

    def _clear_selection(self):
        """Limpia la selección rubber-band."""
        self._last_valid_rect = QRect()
        if self._rubber_band:
            self._rubber_band.hide()
            self._rubber_band.setGeometry(0, 0, 0, 0)
        self._origin = QPointF()
        self.crop_changed.emit()

    def clear_selection(self):
        """Limpia la selección (público, para Reintentar recorte)."""
        self._clear_selection()

    def set_crop_rect(self, rect: tuple[int, int, int, int] | None):
        """
        Restaura la selección de recorte desde coordenadas de escena (x, y, w, h).
        Útil para recuperar el estado al cambiar entre imágenes.
        """
        if rect is None or self._display_np is None:
            self._clear_selection()
            return
        x, y, w, h = rect
        if w < 5 or h < 5:
            self._clear_selection()
            return
        top_left = self.mapFromScene(QPointF(x, y))
        bottom_right = self.mapFromScene(QPointF(x + w, y + h))
        if self._rubber_band is None:
            self._rubber_band = QRubberBand(QRubberBand.Shape.Rectangle, self.viewport())
        rx = min(top_left.x(), bottom_right.x())
        ry = min(top_left.y(), bottom_right.y())
        rw = abs(bottom_right.x() - top_left.x())
        rh = abs(bottom_right.y() - top_left.y())
        self._last_valid_rect = QRect(int(rx), int(ry), int(rw), int(rh))
        self._rubber_band.setGeometry(self._last_valid_rect)
        self._rubber_band.show()
        self.crop_changed.emit()

    def get_current_crop(self) -> tuple[int, int, int, int] | None:
        """
        Devuelve (x, y, w, h) en coordenadas de la imagen mostrada (con rotación).
        Si no hay selección válida, devuelve None.
        """
        if not self._rubber_band or not self._rubber_band.isVisible():
            return None
        geom = self._rubber_band.geometry()
        if geom.width() < 5 or geom.height() < 5:
            return None
        # Rubber band está en viewport; geometry() da coords del viewport
        top_left = self.mapToScene(geom.topLeft())
        bottom_right = self.mapToScene(geom.bottomRight())
        if self._pix_item is None:
            return None
        # Coordenadas en la escena (que es la imagen mostrada)
        x1 = int(max(0, top_left.x()))
        y1 = int(max(0, top_left.y()))
        x2 = int(min(self._display_np.shape[1] if self._display_np is not None else 0, bottom_right.x()))
        y2 = int(min(self._display_np.shape[0] if self._display_np is not None else 0, bottom_right.y()))
        if x2 <= x1 or y2 <= y1:
            return None
        return (x1, y1, x2 - x1, y2 - y1)

    def get_cropped_image(self) -> np.ndarray | None:
        """Devuelve el recorte como numpy (imagen mostrada, ya rotada)."""
        rect = self.get_current_crop()
        if rect is None or self._display_np is None:
            return None
        x, y, w, h = rect
        return self._display_np[y : y + h, x : x + w].copy()

    def reset_view(self):
        """Ajusta la vista a la imagen."""
        if self._scene.sceneRect().isValid():
            self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
            self._last_zoom = 1.0

    def wheelEvent(self, event: QWheelEvent):
        """Zoom con rueda del ratón."""
        if self._image_np is None:
            return
        factor = ZOOM_FACTOR if event.angleDelta().y() > 0 else 1 / ZOOM_FACTOR
        self.scale(factor, factor)
        self._last_zoom *= factor
        event.accept()

    def mousePressEvent(self, event: QMouseEvent):
        if self._image_np is None:
            return
        if event.button() == Qt.MouseButton.MiddleButton or (
            event.button() == Qt.MouseButton.LeftButton and self._space_pressed
        ):
            self._panning = True
            self._pan_start = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self._origin = self.mapToScene(event.position().toPoint())
            if self._rubber_band is None:
                self._rubber_band = QRubberBand(QRubberBand.Shape.Rectangle, self.viewport())
            # Iniciar nueva selección; si fue solo un clic, restauraremos la anterior en release
            self._rubber_band.setGeometry(0, 0, 0, 0)
            self._rubber_band.show()
            self._rubber_origin_view = event.position().toPoint()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._panning:
            delta = event.position() - self._pan_start
            self._pan_start = event.position()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - int(delta.x())
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - int(delta.y())
            )
            event.accept()
            return
        # Solo actualizar rectángulo durante arrastre (botón izquierdo pulsado)
        if (event.buttons() & Qt.MouseButton.LeftButton and self._rubber_band
                and self._rubber_band.isVisible() and self._rubber_origin_view is not None):
            pt = event.position().toPoint()
            x1, y1 = self._rubber_origin_view.x(), self._rubber_origin_view.y()
            x2, y2 = pt.x(), pt.y()
            if self._square_mode:
                side = min(abs(x2 - x1), abs(y2 - y1))
                if x2 < x1:
                    x2 = x1 - side
                else:
                    x2 = x1 + side
                if y2 < y1:
                    y2 = y1 - side
                else:
                    y2 = y1 + side
            x = min(x1, x2)
            y = min(y1, y2)
            w = abs(x2 - x1)
            h = abs(y2 - y1)
            self._rubber_band.setGeometry(x, y, w, h)
            self.crop_changed.emit()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.MiddleButton or (
            event.button() == Qt.MouseButton.LeftButton and self._space_pressed
        ):
            self._panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return
        if event.button() == Qt.MouseButton.LeftButton and self._rubber_band:
            geom = self._rubber_band.geometry()
            # Si fue un clic sin arrastrar (rectángulo muy pequeño), restaurar selección anterior
            if geom.width() < 5 or geom.height() < 5:
                if self._last_valid_rect.width() >= 5 and self._last_valid_rect.height() >= 5:
                    self._rubber_band.setGeometry(self._last_valid_rect)
                    self._rubber_band.show()
                else:
                    self._rubber_band.hide()  # No había selección previa; ocultar
            else:
                self._last_valid_rect = geom  # Guardar para que la selección persista
            self._rubber_origin_view = None  # Fin del arrastre
            self.crop_changed.emit()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def eventFilter(self, obj, event):
        """Captura eventos del viewport para coordenadas correctas."""
        if obj == self.viewport():
            if event.type() == QEvent.Type.MouseButtonPress:
                self.mousePressEvent(event)
                return True
            if event.type() == QEvent.Type.MouseMove:
                self.mouseMoveEvent(event)
                return True
            if event.type() == QEvent.Type.MouseButtonRelease:
                self.mouseReleaseEvent(event)
                return True
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Space:
            self._space_pressed = True
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key.Key_Space:
            self._space_pressed = False
            if self._panning:
                self._panning = False
                self.setCursor(Qt.CursorShape.ArrowCursor)
        super().keyReleaseEvent(event)

    @property
    def rotation_deg(self) -> int:
        return self._rotation_deg
