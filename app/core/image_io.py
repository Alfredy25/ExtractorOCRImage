"""Carga y conversión de imágenes OpenCV <-> Qt."""
from pathlib import Path

import cv2
import numpy as np
from PySide6.QtGui import QImage, QPixmap


def load_image(path: Path) -> np.ndarray | None:
    """Carga una imagen desde disco como BGR (OpenCV)."""
    img = cv2.imread(str(path))
    if img is None:
        return None
    return img


def np_to_qpixmap(arr: np.ndarray) -> QPixmap:
    """Convierte numpy (BGR) a QPixmap (RGB)."""
    if arr is None or arr.size == 0:
        return QPixmap()
    h, w = arr.shape[:2]
    if len(arr.shape) == 2:
        bytes_per_line = w
        fmt = QImage.Format.Format_Grayscale8
        img = QImage(arr.data, w, h, bytes_per_line, fmt)
    else:
        rgb = cv2.cvtColor(arr, cv2.COLOR_BGR2RGB)
        bytes_per_line = rgb.strides[0]
        fmt = QImage.Format.Format_RGB888
        img = QImage(rgb.data, w, h, bytes_per_line, fmt)
    return QPixmap.fromImage(img.copy())


def qimage_to_np(qimg: QImage) -> np.ndarray:
    """Convierte QImage a numpy BGR."""
    fmt = qimg.format()
    if fmt == QImage.Format.Format_RGB888:
        arr = np.array(qimg.bits().asarray(qimg.sizeInBytes())).reshape(
            qimg.height(), qimg.width(), 3
        )
        return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    elif fmt == QImage.Format.Format_Grayscale8:
        arr = np.array(qimg.bits().asarray(qimg.sizeInBytes())).reshape(
            qimg.height(), qimg.width()
        )
        return arr
    else:
        qimg_rgb = qimg.convertToFormat(QImage.Format.Format_RGB888)
        arr = np.array(qimg_rgb.bits().asarray(qimg_rgb.sizeInBytes())).reshape(
            qimg_rgb.height(), qimg_rgb.width(), 3
        )
        return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
