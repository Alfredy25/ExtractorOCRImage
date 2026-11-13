"""Combo editable que busca en un catálogo y permite dar de alta un registro."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from app.components.theme import SPACE
from app.components.widgets import field_label, subtitle, text_button
from app.services.catalogs_service import (
    CatalogConflictError,
    CatalogSessionExpiredError,
)
from app.states.workers.callable_worker import run_worker
from app.views.session_relogin import prompt_relogin_after_session_expired
from app.models.receiver import ESTADOS_MX


class _NoWheelComboBox(QComboBox):
    def wheelEvent(self, event: QWheelEvent) -> None:
        event.ignore()


def _write_normalized(field: QLineEdit, normalizer: Callable[[str], str]) -> None:
    field.setText(normalizer(field.text()))


class _QuickCreateDialog(QDialog):
    """Alta mínima de un catálogo: los campos que declare quien lo abre."""

    def __init__(
        self,
        title: str,
        fields: list[tuple[str, str, str, int]],
        parent: QWidget | None = None,
        field_normalizers: dict[str, Callable[[str], str]] | None = None,
        normalize_together: bool = False,
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self._values: dict[str, str] = {}
        self._inputs: list[tuple[str, str, QWidget]] = []
        self._normalizers = field_normalizers or {}
        self._normalize_together = normalize_together and bool(self._normalizers)

        root = QVBoxLayout(self)
        root.setContentsMargins(SPACE["lg"], SPACE["md"], SPACE["lg"], SPACE["md"])
        root.setSpacing(SPACE["sm"])
        heading = QLabel(title)
        heading.setProperty("role", "headline")
        root.addWidget(heading)

        for key, label, kind, limit in fields:
            root.addWidget(field_label(label))
            if kind == "state":
                widget: QWidget = _NoWheelComboBox()
                combo = widget
                combo.addItem("Seleccione", "")
                for estado in ESTADOS_MX:
                    combo.addItem(estado, estado)
            else:
                widget = QLineEdit()
                if limit:
                    widget.setMaxLength(limit)
                if kind == "upper":
                    widget.textEdited.connect(
                        lambda text, field=widget: _force_upper(field, text)
                    )
            normalizer = None if self._normalize_together or kind == "state" else self._normalizers.get(key)
            if normalizer is None:
                root.addWidget(widget)
            else:
                row = QHBoxLayout()
                row.setContentsMargins(0, 0, 0, 0)
                row.setSpacing(SPACE["xs"])
                row.addWidget(widget, 1)
                button = text_button("Normalizar", variant="ghost")
                button.clicked.connect(
                    lambda _checked=False, field=widget, fn=normalizer: _write_normalized(field, fn)
                )
                row.addWidget(button, 0, Qt.AlignmentFlag.AlignVCenter)
                root.addLayout(row)
            self._inputs.append((key, kind, widget))

        if self._normalize_together:
            together = QHBoxLayout()
            together.setContentsMargins(0, 0, 0, 0)
            button = text_button("Normalizar", variant="ghost")
            button.clicked.connect(self._normalize_all)
            together.addWidget(button)
            together.addStretch(1)
            root.addLayout(together)

        self._error = subtitle("")
        self._error.setProperty("role", "subtitle")
        root.addWidget(self._error)

        actions = QHBoxLayout()
        actions.addStretch(1)
        cancel = text_button("Cancelar", variant="ghost")
        cancel.clicked.connect(self.reject)
        save = text_button("Guardar", variant="primary", icon="save")
        save.clicked.connect(self._save)
        actions.addWidget(cancel)
        actions.addWidget(save)
        root.addLayout(actions)
        self.resize(600, 220 + 48 * len(fields))

    def values(self) -> dict[str, str]:
        return dict(self._values)

    def _normalize_all(self) -> None:
        for key, kind, widget in self._inputs:
            normalizer = self._normalizers.get(key)
            if normalizer is None or kind == "state" or not isinstance(widget, QLineEdit):
                continue
            widget.setText(normalizer(widget.text()))

    def _save(self) -> None:
        collected: dict[str, str] = {}
        for key, kind, widget in self._inputs:
            if kind == "state":
                collected[key] = str(widget.currentData() or "")
            else:
                collected[key] = widget.text().strip()
            if not collected[key]:
                self._error.setText("Complete todos los campos.")
                return
        self._values = collected
        self.accept()


def _force_upper(field: QLineEdit, text: str) -> None:
    upper = text.upper()
    if upper == text:
        return
    pos = field.cursorPosition()
    field.blockSignals(True)
    field.setText(upper)
    field.setCursorPosition(pos)
    field.blockSignals(False)


class AutocompleteComboBox(QWidget):
    """Buscador con debounce. El valor elegido es el DTO, no el texto libre."""

    selection_changed = Signal()

    def __init__(
        self,
        search_fn: Callable[[str], list[Any]],
        label_fn: Callable[[Any], str],
        create_fn: Callable[[dict[str, str]], Any] | None = None,
        create_title: str = "Nuevo registro",
        create_fields: list[tuple[str, str, str, int]] | None = None,
        field_normalizers: dict[str, Callable[[str], str]] | None = None,
        normalize_together: bool = False,
        placeholder: str = "",
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._search_fn = search_fn
        self._label_fn = label_fn
        self._create_fn = create_fn
        self._create_title = create_title
        self._create_fields = create_fields or []
        self._field_normalizers = field_normalizers or {}
        self._normalize_together = normalize_together
        self._results: list[Any] = []
        self._selected: Any = None
        self._generation = 0

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(SPACE["xs"])

        self._combo = _NoWheelComboBox()
        self._combo.setEditable(True)
        self._combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self._combo.lineEdit().setPlaceholderText(placeholder)
        self._combo.activated.connect(self._on_activated)
        self._combo.lineEdit().textEdited.connect(self._on_edited)
        row.addWidget(self._combo, 1)

        self._create_button = text_button("Crear", variant="ghost", icon="add")
        self._create_button.setVisible(create_fn is not None)
        self._create_button.clicked.connect(self._on_create)
        row.addWidget(self._create_button)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(350)
        self._timer.timeout.connect(self._start_search)

        self._status = subtitle("")
        self._status.setVisible(False)

    def status_widget(self) -> QWidget:
        """La etiqueta de estado va debajo del combo, en el layout del padre."""
        return self._status

    def selected(self) -> Any:
        return self._selected

    def text(self) -> str:
        return self._combo.currentText().strip()

    def set_text(self, value: str) -> None:
        """Deja el texto escrito, sin elegir un registro del catálogo."""
        self._selected = None
        self._combo.setEditText(value.strip())
        self._set_status("")

    def set_selected(self, item: Any) -> None:
        self._selected = item
        self._results = [item]
        self._combo.blockSignals(True)
        self._combo.clear()
        self._combo.addItem(self._label_fn(item), 0)
        self._combo.setCurrentIndex(0)
        self._combo.blockSignals(False)
        self._set_status("")
        self.selection_changed.emit()

    def clear_selection(self) -> None:
        if self._selected is None:
            return
        self._selected = None
        self.selection_changed.emit()

    def _on_edited(self, _text: str) -> None:
        if self._selected is not None and self._label_fn(self._selected) != self._combo.currentText():
            self._selected = None
            self.selection_changed.emit()
        self._timer.start()

    def _on_activated(self, index: int) -> None:
        data = self._combo.itemData(index)
        if isinstance(data, int) and 0 <= data < len(self._results):
            self._selected = self._results[data]
            self.selection_changed.emit()

    def _start_search(self) -> None:
        text = self._combo.currentText().strip()
        self._generation += 1
        generation = self._generation
        if self._selected is not None and self._label_fn(self._selected) == text:
            self._set_status("")
            return
        if len(text) < 3:
            self._set_status("Escriba al menos 3 caracteres.")
            return
        self._set_status("Buscando…")
        run_worker(
            self,
            lambda: self._search_fn(text),
            lambda items, gen=generation: self._on_results(gen, items),
            lambda exc, gen=generation: self._on_fail(gen, exc),
        )

    def _on_results(self, generation: int, items: list[Any]) -> None:
        if generation != self._generation:
            return
        text = self._combo.currentText()
        self._results = list(items or [])
        self._combo.blockSignals(True)
        self._combo.clear()
        for index, item in enumerate(self._results):
            self._combo.addItem(self._label_fn(item), index)
        self._combo.setEditText(text)
        self._combo.blockSignals(False)
        count = len(self._results)
        if count == 0:
            self._set_status("Sin coincidencias. Puede crear el registro.")
            return
        self._set_status(f"{count} coincidencia" if count == 1 else f"{count} coincidencias")
        self._combo.showPopup()

    def _on_fail(self, generation: int, exc: Exception) -> None:
        if generation != self._generation:
            return
        if isinstance(exc, CatalogSessionExpiredError):
            self._set_status("")
            prompt_relogin_after_session_expired(self, str(exc))
            return
        self._set_status(str(exc))

    def _set_status(self, text: str) -> None:
        self._status.setText(text)
        self._status.setVisible(bool(text))

    def _on_create(self) -> None:
        if self._create_fn is None:
            return
        dialog = _QuickCreateDialog(
            self._create_title,
            self._create_fields,
            self.window(),
            field_normalizers=self._field_normalizers,
            normalize_together=self._normalize_together,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        values = dialog.values()
        self._create_button.setEnabled(False)
        run_worker(
            self,
            lambda: self._create_fn(values),
            self._on_created,
            self._on_create_failed,
        )

    def _on_created(self, item: Any) -> None:
        self._create_button.setEnabled(True)
        self.set_selected(item)

    def _on_create_failed(self, exc: Exception) -> None:
        self._create_button.setEnabled(True)
        if isinstance(exc, CatalogSessionExpiredError):
            prompt_relogin_after_session_expired(self, str(exc))
            return
        if isinstance(exc, CatalogConflictError):
            QMessageBox.information(self, "Ya existe", str(exc))
            return
        QMessageBox.critical(self, "No se pudo crear", str(exc))
