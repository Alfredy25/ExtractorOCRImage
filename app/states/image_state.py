"""Caché temporal del trabajo pendiente por imagen."""

from __future__ import annotations

from pathlib import Path


class ImageStateStore:
    """Almacena el estado de imágenes aún no guardadas."""

    def __init__(self) -> None:
        self._states: dict[str, dict] = {}

    def get(self, path: Path) -> dict | None:
        return self._states.get(str(path))

    def save(self, path: Path, state: dict) -> None:
        self._states[str(path)] = state

    def remove(self, path: Path) -> None:
        self._states.pop(str(path), None)
