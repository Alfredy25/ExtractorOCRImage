"""Panel derecho: enviar a IA, formulario de campos, guardar."""
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QTextEdit,
                                QFormLayout, QLineEdit, QLabel, QScrollArea, 
                                QProgressBar, QWidget)

from app.models.field_schema import FIELD_KEYS


class RightPanel(QWidget):
    """Panel con botón Enviar a IA, formulario y guardar."""

    send_to_ai_clicked = Signal()
    check_coverage_clicked = Signal()
    save_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._fields: dict[str, QLineEdit] = {}
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        self._btn_send = QPushButton("Enviar a IA")
        self._btn_send.clicked.connect(self.send_to_ai_clicked.emit)
        layout.addWidget(self._btn_send)

        self._btn_coverage = QPushButton("Consultar Cobertura")
        self._btn_coverage.clicked.connect(self.check_coverage_clicked.emit)
        layout.addWidget(self._btn_coverage)

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)  # Indeterminado
        self._progress.hide()
        layout.addWidget(self._progress)

        layout.addWidget(QLabel("Texto bruto (destinatario_raw):"))
        self._destinatario_raw = QTextEdit()
        self._destinatario_raw.setMaximumHeight(100)
        layout.addWidget(self._destinatario_raw)

        form = QFormLayout()
        for key in FIELD_KEYS:
            le = QLineEdit()
            le.setPlaceholderText(key.replace("_", " "))
            self._fields[key] = le
            label = (
                "Numero de volante"
                if key == "numero_volante"
                else key.replace("_", " ").title()
            )
            form.addRow(label + ":", le)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        form_widget = QWidget()
        form_widget.setLayout(form)
        scroll.setWidget(form_widget)
        layout.addWidget(scroll)

        layout.addWidget(QLabel("Observaciones IA:"))
        self._observaciones = QTextEdit()
        self._observaciones.setMaximumHeight(80)
        layout.addWidget(self._observaciones)

        btn_save = QPushButton("Guardar registro")
        btn_save.clicked.connect(self.save_clicked.emit)
        layout.addWidget(btn_save)

        layout.addStretch()

    def set_send_enabled(self, enabled: bool):
        self._btn_send.setEnabled(enabled)

    def set_loading(self, loading: bool):
        self._btn_send.setEnabled(not loading)
        self._progress.setVisible(loading)

    def set_result(self, data: dict):
        """Rellena el formulario con el resultado de la IA."""
        self.set_form_data(data)

    def set_form_data(self, data: dict):
        """Rellena el formulario con datos (IA o restaurados)."""
        self._destinatario_raw.setPlainText(data.get("destinatario_raw", "") or "")
        campos = data.get("campos") or {}
        for key, le in self._fields.items():
            le.setText(campos.get(key, "") or "")
        self._observaciones.setPlainText(data.get("observaciones_ia", "") or "")

    def get_form_data(self) -> dict:
        """Devuelve los datos del formulario para guardar."""
        result = {"destinatario_raw": self._destinatario_raw.toPlainText().strip()}
        result["campos"] = {k: le.text().strip() for k, le in self._fields.items()}
        result["observaciones_ia"] = self._observaciones.toPlainText().strip()
        return result

    def clear_form(self):
        self._destinatario_raw.clear()
        for le in self._fields.values():
            le.clear()
        self._observaciones.clear()
