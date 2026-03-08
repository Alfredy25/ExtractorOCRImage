"""Herramientas de recorte y rotación de imágenes."""
import numpy as np


def apply_rotation(image: np.ndarray, deg: int) -> np.ndarray:
    """Aplica rotación a la imagen. deg debe ser uno de -90, 90, 180."""
    if deg == 0:
        return image.copy()
    if deg == 90:
        return np.rot90(image, k=-1).copy()
    if deg == -90 or deg == 270:
        return np.rot90(image, k=1).copy()
    if deg == 180:
        return np.rot90(image, k=2).copy()
    # Deg no estándar: usar cv2
    import cv2
    h, w = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, deg, 1.0)
    return cv2.warpAffine(image, M, (w, h))


def apply_crop(image: np.ndarray, rect: tuple[int, int, int, int]) -> np.ndarray:
    """Recorta la imagen según (x, y, w, h)."""
    x, y, w, h = rect
    h_img, w_img = image.shape[:2]
    x = max(0, min(x, w_img - 1))
    y = max(0, min(y, h_img - 1))
    w = min(w, w_img - x)
    h = min(h, h_img - y)
    if w <= 0 or h <= 0:
        return image.copy()
    return image[y : y + h, x : x + w].copy()
