"""Hilo corto para una llamada de red disparada desde la interfaz."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, QThread, Signal


class CallableWorker(QThread):
    """Ejecuta ``fn`` fuera del hilo de la interfaz."""

    succeeded = Signal(object)
    failed = Signal(object)

    def __init__(self, fn: Callable[[], object], parent: QObject | None = None):
        super().__init__(parent)
        self._fn = fn

    def run(self) -> None:
        try:
            self.succeeded.emit(self._fn())
        except Exception as exc:
            self.failed.emit(exc)


def run_worker(
    owner: QObject,
    fn: Callable[[], object],
    on_ok: Callable,
    on_err: Callable,
) -> CallableWorker:
    """Lanza ``fn`` y entrega el resultado en el hilo de ``owner``."""
    worker = CallableWorker(fn, owner)
    holder = getattr(owner, "_bg_workers", None)
    if holder is None:
        holder = []
        setattr(owner, "_bg_workers", holder)
    holder.append(worker)

    def _release(*_args: object) -> None:
        if worker in holder:
            holder.remove(worker)

    worker.succeeded.connect(on_ok)
    worker.failed.connect(on_err)
    worker.succeeded.connect(_release)
    worker.failed.connect(_release)
    worker.start()
    return worker
