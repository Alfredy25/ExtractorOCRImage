"""Renderiza las pantallas y comprueba interacciones críticas sin abrir ventanas.

Sirve para revisar el resultado visual del tema y detectar regresiones de
interacción que no se ven en una captura: por ejemplo, un widget superpuesto que
se coma los clics de otro.

Uso:

    python scripts/preview_ui.py [carpeta_de_salida]

Se ejecuta con la plataforma «offscreen» de Qt, así que no requiere pantalla.
Devuelve código 1 si alguna comprobación falla.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

# Debe fijarse antes de crear la QApplication.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np  # noqa: E402
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt  # noqa: E402
from PySide6.QtGui import QMouseEvent  # noqa: E402
from PySide6.QtWidgets import QApplication, QScrollArea, QWidget  # noqa: E402

from app.components.theme import apply_theme  # noqa: E402

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.gettempdir()) / "extractor_ocr_preview"
OUT.mkdir(parents=True, exist_ok=True)

app = QApplication(["preview"])
apply_theme()

FAILURES: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    status = "OK  " if condition else "FAIL"
    print(f"[{status}] {name} {detail}")
    if not condition:
        FAILURES.append(name)


def shot(widget: QWidget, name: str, width: int, height: int) -> None:
    widget.show()
    # Se redimensiona después de mostrar: algunos diálogos no aceptan el tamaño
    # hasta que su layout se ha calculado y la captura saldría recortada.
    widget.resize(width, height)
    for _ in range(3):
        app.processEvents()
    pixmap = widget.grab()
    pixmap.save(str(OUT / f"{name}.png"))
    print(f"       -> {name}.png {pixmap.width()}x{pixmap.height()}")


def synthetic_envelope(path: Path) -> Path:
    """Sobre sintético con texto, para ver el visor con contenido realista."""
    import cv2

    img = np.full((900, 1400, 3), 238, dtype=np.uint8)
    cv2.rectangle(img, (40, 40), (1360, 860), (200, 200, 200), 2)
    lines = [
        "LIC. MARIA FERNANDA GARCIA LOPEZ",
        "DIRECTORA DE ADMINISTRACION",
        "AV. INSURGENTES SUR 1234, INT 5B",
        "COL. FLORIDA, ALVARO OBREGON",
        "CIUDAD DE MEXICO  C.P. 01030",
        "TEL. 55 1234 5678",
    ]
    y = 260
    for line in lines:
        cv2.putText(img, line, (150, y), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (25, 25, 25), 2)
        y += 60
    cv2.imwrite(str(path), img)
    return path


def click(widget: QWidget) -> None:
    """Pulsa el widget en su centro, como lo haría el usuario."""
    center = QPoint(widget.width() // 2, widget.height() // 2)
    for event_type, buttons, button in (
        (QEvent.Type.MouseButtonPress, Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton),
        (QEvent.Type.MouseButtonRelease, Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton),
    ):
        event = QMouseEvent(
            event_type,
            QPointF(center),
            QPointF(widget.mapToGlobal(center)),
            button,
            buttons,
            Qt.KeyboardModifier.NoModifier,
        )
        QApplication.sendEvent(widget, event)
    app.processEvents()


def receives_mouse(widget: QWidget) -> bool:
    """Comprueba que el ratón llega al widget en su posición en pantalla.

    Recorre la jerarquía como lo hace Qt al repartir los clics: si un ancestro es
    transparente al ratón, ``childAt`` no devuelve el widget y el usuario no
    puede pulsarlo aunque se vea perfectamente.
    """
    window = widget.window()
    center = QPoint(widget.width() // 2, widget.height() // 2)
    target = window.childAt(window.mapFromGlobal(widget.mapToGlobal(center)))
    while target is not None:
        if target is widget:
            return True
        target = target.parentWidget()
    return False


# --- 1. Login ------------------------------------------------------------
from app.views.login_window import LoginWindow  # noqa: E402

login = LoginWindow(login_fn=lambda email, password: None)
shot(login, "01_login", 520, 640)
login._on_failure("Credenciales incorrectas. Verifica tu correo y contraseña.")
shot(login, "02_login_error", 520, 640)
check("login: campos y boton presentes", bool(login._email and login._pass and login._btn_login))
check("login: boton recibe el raton", receives_mouse(login._btn_login))
login.close()

# --- 2. Ventana principal ------------------------------------------------
from app.views.main_window import MainWindow  # noqa: E402

window = MainWindow()
shot(window, "03_workspace_vacio", 1500, 940)

image_path = synthetic_envelope(OUT / "sobre_demo.png")
window._queue.add_images([image_path, OUT / "sobre_demo.png"])
window._on_image_activated(image_path)
app.processEvents()
check("workspace: imagen cargada", window._current_image_np is not None)
check("workspace: cola sin duplicados", window._queue.count() == 1, f"count={window._queue.count()}")

# Datos OCR de ejemplo para ver el inspector poblado.
window._right.set_result({
    "destinatario_raw": "LIC. MARIA FERNANDA GARCIA LOPEZ\nDIRECTORA DE ADMINISTRACION",
    "campos": {
        "nombre_titulo": "LIC. MARIA FERNANDA GARCIA LOPEZ",
        "cargo_dependencia": "DIRECTORA DE ADMINISTRACION",
        "direccion": "AV. INSURGENTES SUR 1234, INT 5B",
        "colonia": "FLORIDA",
        "municipio_alcaldia": "ALVARO OBREGON",
        "estado": "CIUDAD DE MEXICO",
        "codigo_postal": "01030",
        "numero_volante": "V-2026-00841",
        "extras": "Entrega en recepcion",
        "contacto": "5512345678",
        "indicaciones": "Edificio G, entrada principal",
    },
    "observaciones_ia": "Codigo postal legible. Colonia con baja confianza.",
})
window._right._sede_combo.setCurrentIndex(1)
app.processEvents()
check("workspace: sede seleccionada", window._right.sede() == "AJUSCO", f"sede={window._right.sede()}")
shot(window, "04_workspace_datos", 1500, 940)

# El HUD flota sobre el lienzo: sus botones deben ser pulsables y, a la vez, el
# resto del lienzo debe seguir recibiendo el arrastre del recorte.
viewer = window._viewer
hud = window._hud
check("HUD: visible", hud.isVisible())
check("HUD: controles habilitados con imagen", hud._btn_zoom_in.isEnabled())
for name, button in (
    ("rotar izquierda", hud._btn_rotate_left),
    ("rotar derecha", hud._btn_rotate_right),
    ("acercar", hud._btn_zoom_in),
    ("alejar", hud._btn_zoom_out),
    ("ajustar", hud._btn_fit),
    ("recorte 1:1", hud._btn_square),
):
    check(f"HUD: el boton de {name} recibe el raton", receives_mouse(button))

before = viewer.rotation_deg
click(hud._btn_rotate_right)
check(
    "HUD: el clic en rotar derecha rota la imagen",
    viewer.rotation_deg == (before + 90) % 360,
    f"{before} -> {viewer.rotation_deg}",
)
click(hud._btn_rotate_left)
check(
    "HUD: el clic en rotar izquierda deshace la rotacion",
    viewer.rotation_deg == before,
    f"rot={viewer.rotation_deg}",
)

zoom_before = viewer.transform().m11()
click(hud._btn_zoom_in)
check(
    "HUD: el clic en acercar cambia el zoom",
    viewer.transform().m11() > zoom_before,
    f"{zoom_before:.3f} -> {viewer.transform().m11():.3f}",
)
click(hud._btn_fit)
check("HUD: el clic en ajustar reencuadra", viewer.transform().m11() != 0)

click(hud._btn_square)
check("HUD: el clic en recorte 1:1 propaga el modo", viewer._square_mode is True)
click(hud._btn_square)
check("HUD: recorte 1:1 se desactiva", viewer._square_mode is False)

viewport = viewer.viewport()
start = QPoint(int(viewport.width() * 0.25), int(viewport.height() * 0.35))
end = QPoint(int(viewport.width() * 0.75), int(viewport.height() * 0.65))


def drag(pos_from: QPoint, pos_to: QPoint) -> None:
    for event_type, pos, buttons, button in (
        (QEvent.Type.MouseButtonPress, pos_from, Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton),
        (QEvent.Type.MouseMove, pos_to, Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton),
        (QEvent.Type.MouseButtonRelease, pos_to, Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton),
    ):
        event = QMouseEvent(
            event_type,
            QPointF(pos),
            QPointF(viewport.mapToGlobal(pos)),
            button,
            buttons,
            Qt.KeyboardModifier.NoModifier,
        )
        QApplication.sendEvent(viewport, event)
        app.processEvents()


drag(start, end)
crop = viewer.get_current_crop()
check("visor: seleccion de recorte con el HUD encima", crop is not None, f"rect={crop}")
check("visor: el lienzo recibe el raton", receives_mouse(viewport))

window._on_apply_crop()
app.processEvents()
check("visor: recorte aplicado", window._current_crop_np is not None)
check(
    "workspace: boton Enviar a IA habilitado tras sede+recorte",
    window._right._btn_send.isEnabled(),
)
shot(window, "05_workspace_recorte", 1500, 940)

# --- 3. Ventana de envios -----------------------------------------------
from app.models.shipping import CoverageItem  # noqa: E402
from app.views.shipment_window import ShipmentWindow  # noqa: E402

coverages = [
    CoverageItem(
        postal_code="01030",
        colony="FLORIDA",
        municipality="ALVARO OBREGON",
        city="CIUDAD DE MEXICO",
        state="CIUDAD DE MEXICO",
        coverage_type="PAQUETEXPRESS",
    ),
    CoverageItem(
        postal_code="01030",
        colony="AXOTLA",
        municipality="ALVARO OBREGON",
        city="CIUDAD DE MEXICO",
        state="CIUDAD DE MEXICO",
        coverage_type="PAQUETEXPRESS",
    ),
]
ocr_data = window._right.get_form_data()
shipment = ShipmentWindow(coverages, ocr_data)
shot(shipment, "06_envios", 1500, 940)

check("envios: 16 campos de envio", len(shipment._shipment_fields) == 16, f"n={len(shipment._shipment_fields)}")
check("envios: 4 campos de cobertura", len(shipment._coverage_fields) == 4)
check("envios: 9 campos OCR", len(shipment._ocr_reference_fields) == 9)
check("envios: 2 colonias en combo", shipment._colony_combo.count() == 2)
check(
    "envios: borrador inicial desde OCR",
    shipment._shipment_fields["name_receiver"].text() == "LIC. MARIA FERNANDA GARCIA LOPEZ",
    shipment._shipment_fields["name_receiver"].text(),
)
check("envios: pais fijo MEXICO", shipment._shipment_fields["country"].text() == "MEXICO")
check("envios: pais no editable", shipment._shipment_fields["country"].isReadOnly())
check("envios: CP de cobertura", shipment._coverage_fields["postal_code"].text() == "01030")

# Cambiar colonia debe refrescar ciudad/estado/tipo sin repisar el borrador.
shipment._colony_combo.setCurrentIndex(1)
app.processEvents()
payload = shipment._shipment_payload_from_form()
check("envios: colonia del payload sigue la seleccion", payload["colony"] == "AXOTLA", payload["colony"])
check("envios: payload trae 21 claves", len(payload) == 21, f"n={len(payload)}")
check(
    "envios: valores iniciales por defecto",
    payload["quantity"] == 1 and payload["package_code"] == 1 and payload["content"],
    f"qty={payload['quantity']} code={payload['package_code']} content={payload['content']!r}",
)
check(
    "envios: comments en payload del formulario",
    bool(payload.get("comments")),
    repr(payload.get("comments")),
)
shot(shipment, "07_envios_colonia", 1500, 940)

# El formulario de envío es largo: se baja el scroll para revisar los campos de
# paquete (cantidad, peso y medidas), que usan controles numéricos.
scroll = shipment.findChild(QScrollArea)
check("envios: formulario con scroll", scroll is not None)
if scroll is not None:
    bar = scroll.verticalScrollBar()
    bar.setValue(bar.maximum())
    app.processEvents()
shot(shipment, "08_envios_paquete", 1500, 940)
shipment.close()

# --- 4. Exportacion -----------------------------------------------------
from app.views.export_dialog import ExportDialog  # noqa: E402

export = ExportDialog()
shot(export, "09_exportar", 620, 640)
check("exportar: combo de sedes con 3 opciones", export._sede.count() == 3)
check("exportar: 2 formatos", export._format.count() == 2)
export.close()
window.close()

print()
print(f"capturas en {OUT}")
if FAILURES:
    print(f"FALLOS ({len(FAILURES)}): " + ", ".join(FAILURES))
    sys.exit(1)
print("Todas las comprobaciones OK")
