"""Diálogo de error por sesión caducada (401) y re-apertura de LoginWindow sobre MainWindow."""

from __future__ import annotations

from PySide6.QtWidgets import QDialog, QMainWindow, QMessageBox, QWidget

from app.ui.login_window import LoginWindow


def _find_main_window(widget: QWidget | None) -> QMainWindow | None:
    p: QWidget | None = widget
    while p is not None:
        if isinstance(p, QMainWindow):
            return p
        p = p.parentWidget()
    return None


def prompt_relogin_after_session_expired(host_widget: QWidget, message: str) -> bool:
    """
    Muestra el error con un único botón «Iniciar sesión de nuevo» (mismos estilos globales
    que el resto de QPushButton). Si el usuario confirma e inicia sesión bien, devuelve
    True y el JWT queda actualizado en ``auth_client``.
    """
    box = QMessageBox(host_widget)
    box.setIcon(QMessageBox.Icon.Critical)
    box.setWindowTitle("Error")
    box.setText(message)
    box.setStandardButtons(QMessageBox.StandardButton.NoButton)
    relogin_btn = box.addButton(
        "Iniciar sesión de nuevo",
        QMessageBox.ButtonRole.AcceptRole,
    )
    box.exec()
    if box.clickedButton() is not relogin_btn:
        return False

    mw = _find_main_window(host_widget)
    parent = mw if mw is not None else host_widget
    dlg = LoginWindow(parent=parent)
    return dlg.exec() == QDialog.DialogCode.Accepted
