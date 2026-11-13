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
from PySide6.QtGui import QMouseEvent, QWheelEvent  # noqa: E402
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
shot(login, "01_login", 520, 680)
login._on_failure("Credenciales incorrectas. Verifica tu correo y contraseña.")
shot(login, "02_login_error", 520, 680)
check("login: campos y boton presentes", bool(login._email and login._pass and login._btn_login and login._remember_user))
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
ocr_sample = {
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
}
window._right.set_result(ocr_sample)
window._right._sede_combo.setCurrentIndex(1)
app.processEvents()
check("workspace: sede seleccionada", window._right.sede() == "AJUSCO", f"sede={window._right.sede()}")
check(
    "workspace: los datos OCR despliegan su seccion",
    window._right._extraction_section.is_expanded(),
)
check("workspace: guardar habilitado con datos OCR", window._right._btn_save.isEnabled())
shot(window, "04_workspace_datos", 1500, 940)

# El flujo arranca por la busqueda de destinatario: esa seccion manda y la de
# extraccion se pliega hasta que haga falta.
window._right.reset_receiver()
app.processEvents()
check("workspace: seccion destinatario desplegada", window._right._receiver_section.is_expanded())
check(
    "workspace: seccion de extraccion plegada al reiniciar",
    not window._right._extraction_section.is_expanded(),
)
check(
    "workspace: crear envio deshabilitado sin destinatario",
    not window._right._btn_create_shipment.isEnabled(),
)
check(
    "workspace: buscador con paginacion y filtros",
    window._right._picker._type_combo.count() == 4
    and window._right._picker._order_combo.count() == 4
    and window._right._picker._direction_combo.count() == 2,
)
check(
    "workspace: el chevron de la seccion recibe el raton",
    receives_mouse(window._right._receiver_section._chevron),
)
click(window._right._receiver_section._chevron)
check(
    "workspace: el clic en el chevron pliega la seccion",
    not window._right._receiver_section.is_expanded(),
)
click(window._right._receiver_section._chevron)
check(
    "workspace: el segundo clic la vuelve a desplegar",
    window._right._receiver_section.is_expanded(),
)
shot(window, "04b_workspace_destinatario", 1500, 940)
window._right.set_form_data(ocr_sample)
app.processEvents()

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

package_keys = {
    "rfc", "email", "package_code", "quantity", "comments", "content",
    "weight", "length", "width", "height",
}
check(
    "envios: campos de paquete",
    set(shipment._shipment_fields) == package_keys,
    f"claves={sorted(shipment._shipment_fields)}",
)
check("envios: 4 campos de cobertura", len(shipment._coverage_fields) == 4)
check("envios: 10 campos OCR", len(shipment._ocr_reference_fields) == 10)
check(
    "envios: referencia con numero de volante",
    shipment._ocr_reference_fields["numero_volante"].text() == "V-2026-00841",
)
check("envios: 2 colonias en combo", shipment._colony_combo.count() == 2)
check("envios: modo alta sin destinatario fijo", shipment._is_alta_mode)
check("envios: alta de destinatario sin buscador", shipment._btn_alta is not None)
check("envios: crear envio deshabilitado sin destinatario", not shipment._btn_submit.isEnabled())
check("envios: RFC por defecto", shipment._shipment_fields["rfc"].text() == "XAXX-010101-000")
check("envios: CP de cobertura", shipment._coverage_fields["postal_code"].text() == "01030")

# Cambiar colonia debe refrescar ciudad/estado/tipo sin repisar el borrador.
shipment._colony_combo.setCurrentIndex(1)
app.processEvents()
payload = shipment._shipment_payload_from_form()
check("envios: colonia del payload sigue la seleccion", payload["colony"] == "AXOTLA", payload["colony"])
check("envios: el paquete no trae destinatario libre", "name_receiver" not in payload)
check("envios: payload de paquete y cobertura", len(payload) == 15, f"n={len(payload)}")
check(
    "envios: email por defecto en alta",
    payload.get("email") == "notificaciones@feuh.com.mx",
    str(payload.get("email")),
)
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

# La rueda del ratón no debe alterar cantidad, código ni medidas al hacer
# scroll sobre el formulario (aunque el puntero esté encima del spinbox).
numeric_keys = ("package_code", "quantity", "weight", "length", "width", "height")
numeric_before = {key: shipment._shipment_fields[key].value() for key in numeric_keys}
for key in numeric_keys:
    widget = shipment._shipment_fields[key]
    wheel = QWheelEvent(
        QPointF(widget.rect().center()),
        QPointF(widget.mapToGlobal(widget.rect().center())),
        QPoint(0, 0),
        QPoint(0, 120),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    )
    QApplication.sendEvent(widget, wheel)
app.processEvents()
numeric_after = {key: shipment._shipment_fields[key].value() for key in numeric_keys}
check(
    "envios: scroll no cambia campos numericos",
    numeric_before == numeric_after,
    f"antes={numeric_before} despues={numeric_after}",
)
colony_before = shipment._colony_combo.currentIndex()
colony_widget = shipment._colony_combo
colony_wheel = QWheelEvent(
    QPointF(colony_widget.rect().center()),
    QPointF(colony_widget.mapToGlobal(colony_widget.rect().center())),
    QPoint(0, 0),
    QPoint(0, 120),
    Qt.MouseButton.NoButton,
    Qt.KeyboardModifier.NoModifier,
    Qt.ScrollPhase.NoScrollPhase,
    False,
)
QApplication.sendEvent(colony_widget, colony_wheel)
app.processEvents()
check(
    "envios: scroll no cambia colonia",
    shipment._colony_combo.currentIndex() == colony_before,
    f"antes={colony_before} despues={shipment._colony_combo.currentIndex()}",
)

# El formulario de envío es largo: se baja el scroll para revisar los campos de
# paquete (cantidad, peso y medidas), que usan controles numéricos.
scroll = shipment.findChild(QScrollArea)
check("envios: formulario con scroll", scroll is not None)
if scroll is not None:
    bar = scroll.verticalScrollBar()
    bar.setValue(bar.maximum())
    app.processEvents()
shot(shipment, "08_envios_paquete", 1500, 940)

# Los diálogos nuevos consultan SEPOMEX y catálogos: en la vista previa no hay red.
from app.models.receiver import Paginated  # noqa: E402
from app.models.sepomex import SepomexDto  # noqa: E402
from app.services import catalogs_service, receivers_service, sepomex_service  # noqa: E402
from app.views.address_dialog import AddressDialog  # noqa: E402
from app.views.receiver_dialog import ReceiverDialog  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

sepomex_service.fetch_sepomex = lambda cp: [
    SepomexDto(
        id=1,
        postal_code=cp,
        settlement="FLORIDA",
        settlement_type="Colonia",
        municipality="ALVARO OBREGON",
        city="CIUDAD DE MEXICO",
        state="CIUDAD DE MEXICO",
        state_code="09",
        zone="Urbano",
    )
]
receivers_service.search_receivers = lambda *_args, **_kwargs: Paginated(
    page=1, page_size=5, total=0, total_pages=0, has_prev=False, has_next=False, items=[]
)
for _name in ("search_titles", "search_job_roles", "search_organizations", "search_volantes"):
    setattr(catalogs_service, _name, lambda *_args, **_kwargs: [])

receiver_dialog = ReceiverDialog(ocr_data)
QTest.qWait(400)
check("destinatario: tipo persona", receiver_dialog._type == "PERSONA")
check(
    "destinatario: nombre OCR en mayusculas",
    receiver_dialog._name.text() == "LIC. MARIA FERNANDA GARCIA LOPEZ",
    receiver_dialog._name.text(),
)
check(
    "destinatario: volante inicial precargado",
    receiver_dialog._volante.text() == "V-2026-00841",
    receiver_dialog._volante.text(),
)
shot(receiver_dialog, "11_crear_destinatario", 1280, 860)
receiver_dialog.close()

address_dialog = AddressDialog(4)
shot(address_dialog, "12_nuevo_domicilio", 720, 640)
check("domicilio: formulario presente", address_dialog._form is not None)
address_dialog.close()

from app.views.contact_dialog import ContactDialog  # noqa: E402

contact_dialog = ContactDialog(4)
shot(contact_dialog, "12b_nuevo_contacto", 480, 260)
check("contacto: telefono presente", contact_dialog._phone is not None)
contact_dialog.close()

from app.views.volante_dialog import VolanteDialog  # noqa: E402

volante_dialog = VolanteDialog(4)
shot(volante_dialog, "12c_nuevo_volante", 560, 320)
check("volante: buscador presente", volante_dialog._volante is not None)
check("volante: boton crear", volante_dialog._volante._create_button.isVisible())
volante_dialog.close()
shipment.close()

# --- 3b. Envio con destinatario existente -------------------------------
# Rama sin OCR: la referencia es el recorte y la cobertura sale del CP del
# domicilio elegido, consultado al abrir la pantalla.
from app.models.receiver import AddressDto, ReceiverDto  # noqa: E402
from app.views import shipment_window as shipment_window_module  # noqa: E402

_AUDIT_TS = "2026-11-10T16:00:00"
_audit = {
    "created_at": _AUDIT_TS,
    "updated_at": _AUDIT_TS,
    "created_by": 1,
    "updated_by": None,
}
sample_address = AddressDto.model_validate({
    "id": 7,
    "street": "AV. INSURGENTES SUR",
    "num_street": "1234",
    "colony": "FLORIDA",
    "municipality": "ALVARO OBREGON",
    "city": "CIUDAD DE MEXICO",
    "state": "CIUDAD DE MEXICO",
    "postal_code": "01030",
    "country": "MEXICO",
    "address_reference": "Edificio G",
    "receiver_id": 4,
    **_audit,
})
sample_receiver = ReceiverDto.model_validate({
    "id": 4,
    "type_entity": "PERSONA",
    "title": {"id": 1, "abbreviation": "LIC.", "meaning": "Licenciada", **_audit},
    "full_name": "MARIA FERNANDA GARCIA LOPEZ",
    "email": "maria.garcia@example.com",
    "position": None,
    "addresses": [sample_address.model_dump()],
    "contacts": [
        {"id": 3, "phone": "5512345678", "ext": "12", "id_destinatario": 4, **_audit},
        {"id": 8, "phone": "5587654321", "ext": None, "id_destinatario": 4, **_audit},
    ],
    "volantes": [
        {"id": 5, "name": "VCS-26-131000-00167", **_audit},
    ],
    **_audit,
})

window._right.show_receiver(sample_receiver, sample_address.id)
app.processEvents()
edit_button = window._right._picker._btn_edit
check("ficha: boton editar destinatario", edit_button is not None and edit_button.isVisible())
add_volante = window._right._picker._btn_add_volante
check("ficha: boton añadir volante", add_volante is not None and add_volante.isVisible())
check("ficha: el boton añadir volante recibe el raton", receives_mouse(add_volante))
volante_lines = window.findChildren(QWidget, "receiverVolanteItem")
check("ficha: lista el volante del destinatario", len(volante_lines) == 1, f"n={len(volante_lines)}")
check("ficha: el boton editar recibe el raton", receives_mouse(edit_button))
contact_choices = window.findChildren(QWidget, "receiverContactChoice")
check("ficha: elegir contacto si hay varios", len(contact_choices) == 2, f"n={len(contact_choices)}")
shot(window, "13b_ficha_editar", 1500, 940)

edit_dialog = ReceiverDialog.for_edit(
    sample_receiver, crop_np=window._current_crop_np, address=sample_address
)
shot(edit_dialog, "14_editar_destinatario", 1280, 860)
QTest.qWait(400)
check("editar destinatario: modo edicion", edit_dialog._is_edit)
check("editar destinatario: tipo bloqueado", not edit_dialog._type_buttons["PERSONA"].isEnabled())
check(
    "editar destinatario: recorte visible",
    edit_dialog.findChild(QWidget, "receiverCropPreview") is not None,
)
check(
    "editar destinatario: agregar domicilio",
    edit_dialog._btn_add_address.isVisible(),
)
check(
    "editar destinatario: editar domicilio",
    edit_dialog._btn_edit_address.isVisible() and edit_dialog._btn_edit_address.isEnabled(),
)
check(
    "editar destinatario: agregar contacto",
    edit_dialog._btn_add_contact.isVisible(),
)
listed_contacts = edit_dialog.findChildren(QWidget, "receiverContactItem")
check(
    "editar destinatario: lista todos los contactos",
    len(listed_contacts) == 2,
    f"n={len(listed_contacts)}",
)
edit_dialog.close()

edit_address = AddressDialog(4, address=sample_address)
QTest.qWait(200)
check("editar domicilio: titulo", edit_address.windowTitle() == "Editar domicilio")
shot(edit_address, "15_editar_domicilio", 720, 640)
edit_address.close()

shipment_window_module.get_coverages_for_postal_code = lambda cp: coverages

shipment_receiver = ShipmentWindow.for_receiver(
    sample_receiver, sample_address, window._current_crop_np
)
# Sin maximizar, la captura respeta el tamaño pedido y se ven las tres columnas.
shipment_receiver.setWindowState(Qt.WindowState.WindowNoState)
QTest.qWait(200)
app.processEvents()
check("envios con destinatario: modo correcto", shipment_receiver._is_receiver_mode)
check("envios con destinatario: sin columna OCR", not shipment_receiver._ocr_reference_fields)
check(
    "envios con destinatario: el recorte es la referencia",
    not shipment_receiver._crop_label.pixmap().isNull(),
)
check(
    "envios con destinatario: cobertura del CP del domicilio",
    shipment_receiver._coverage_fields["postal_code"].text() == "01030",
    shipment_receiver._coverage_fields["postal_code"].text(),
)
check(
    "envios con destinatario: crear envio habilitado",
    shipment_receiver._btn_submit.isEnabled(),
)
receiver_payload = shipment_receiver._payload_from_receiver()
check(
    "envios con destinatario: nombre y calle del directorio",
    receiver_payload["name_receiver"] == "LIC. MARIA FERNANDA GARCIA LOPEZ"
    and receiver_payload["street"] == "AV. INSURGENTES SUR",
    f"{receiver_payload['name_receiver']} / {receiver_payload['street']}",
)
check(
    "envios con destinatario: colonia y CP de la cobertura",
    receiver_payload["colony"] == "FLORIDA" and receiver_payload["postal_code"] == "01030",
)
email_field = shipment_receiver.findChild(QWidget, "shipmentEmailField")
check(
    "envios con destinatario: email por defecto",
    email_field is not None and email_field.text() == "notificaciones@feuh.com.mx",
    "" if email_field is None else email_field.text(),
)
check(
    "envios con destinatario: no usa el correo del directorio",
    receiver_payload.get("email") == "notificaciones@feuh.com.mx",
    str(receiver_payload.get("email")),
)
check(
    "envios con destinatario: telefono del contacto",
    receiver_payload.get("phone") == "5512345678",
    str(receiver_payload.get("phone")),
)
shot(shipment_receiver, "13_envio_destinatario", 1500, 940)
shipment_receiver.close()

# --- 4. Exportacion -----------------------------------------------------
from app.views.export_dialog import ExportDialog  # noqa: E402

export = ExportDialog()
shot(export, "09_exportar", 620, 640)
check("exportar: combo de sedes con 3 opciones", export._sede.count() == 3)
check("exportar: 2 formatos", export._format.count() == 2)
export.close()

# --- 5. Historial de envios --------------------------------------------
from datetime import datetime as _dt  # noqa: E402

from app.models.shipping import ShippingDto  # noqa: E402
from app.views.export_shipments import ExportShipments  # noqa: E402

history = ExportShipments()
history.setWindowState(Qt.WindowState.WindowNoState)
check("historial: combo alcance con 2 opciones", history._scope_combo.count() == 2)
check(
    "historial: alcance por defecto es todos",
    history._my_shipments_filter() is False,
)
history._scope_combo.setCurrentIndex(1)
check(
    "historial: solo mios activa my_shipments",
    history._my_shipments_filter() is True,
)
history._scope_combo.setCurrentIndex(0)
sample = ShippingDto.model_validate(
    {
        "id_shipping": 12,
        "id_folio": 19,
        "name_receiver": "DR. PEPE PINEDO PINEDO",
        "rfc": "XAXX010101000",
        "country": "MEXICO",
        "state": "CIUDAD DE MEXICO",
        "city": "CIUDAD DE MEXICO",
        "colony": "FLORIDA",
        "street": "CTO. CERRO DEL GATO",
        "num_street": "123",
        "postal_code": "01030",
        "email": "destinatario@example.com",
        "phone": "5512345678",
        "address_reference": "Puerta gris",
        "quantity": 1,
        "package_code": 1,
        "content": "DOCUMENTOS LEGALES",
        "weight": "1.00",
        "length": "30.00",
        "width": "20.00",
        "height": "1.00",
        "coverage_type": "PAQUETEXPRESS",
        "comments": "ENTREGAR EN OFICIALIA",
        "created_at": _dt(2026, 8, 11, 18, 1, 12),
    }
)
history.fill_table([sample, sample])
shot(history, "10_historial_envios", 1360, 860)
history.close()
window.close()

print()
print(f"capturas en {OUT}")
if FAILURES:
    print(f"FALLOS ({len(FAILURES)}): " + ", ".join(FAILURES))
    sys.exit(1)
print("Todas las comprobaciones OK")
