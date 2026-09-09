"""Tests del modelo y validación acumulativa de envíos Paquetexpress."""

from app.models.shipping import ShippingRequest, validate_shipping


def _valid_shipment() -> dict:
    return {
        "name_receiver": "DR. PEPE PINEDO PINEDO",
        "rfc": "XAXX010101000",
        "country": "MEXICO",
        "state": "ZACATECAS",
        "city": "CIUDAD GOBIERNO",
        "colony": "COLONIA JUAREZ",
        "street": "CTO. CERRO DEL GATO",
        "num_street": "123",
        "postal_code": "98160",
        "email": "destinatario@example.com",
        "phone": "5555555555",
        "address_reference": "Edificio G",
        "quantity": 1,
        "package_code": 1,
        "content": "DOCUMENTOS LEGALES",
        "comments": "ENTREGAR EN OFICIALIA DE PARTES O RECEPCION",
        "weight": "1.00",
        "length": "30.00",
        "width": "20.00",
        "height": "1.00",
        "coverage_type": "PAQUETEXPRESS",
    }


def test_shipping_request_validates_successfully():
    model, errors = validate_shipping(_valid_shipment())

    assert errors == []
    assert isinstance(model, ShippingRequest)
    dumped = model.model_dump(exclude_none=True)
    assert dumped["postal_code"] == "98160"
    assert dumped["quantity"] == 1
    assert dumped["comments"] == "ENTREGAR EN OFICIALIA DE PARTES O RECEPCION"


def test_shipping_validation_accumulates_multiple_errors():
    payload = _valid_shipment()
    payload.update({
        "name_receiver": "A",
        "email": "correo-invalido",
        "phone": "123",
        "postal_code": "9X1A",
        "package_code": 99,
    })

    _, errors = validate_shipping(payload)
    fields = {error["campo"] for error in errors}

    assert "Destinatario" in fields
    assert "Email" in fields
    assert "Teléfono" in fields
    assert "Código Postal" in fields
    assert "Código de paquete" in fields
    assert len(errors) >= 5


def test_shipping_validation_uses_form_labels():
    payload = _valid_shipment()
    payload.update({
        "name_receiver": "A",
        "num_street": "",
        "address_reference": "x" * 51,
    })

    _, errors = validate_shipping(payload)
    by_field = {error["campo"]: error["error"] for error in errors}

    assert "Destinatario" in by_field
    assert "Número exterior" in by_field
    assert "Referencia de domicilio" in by_field
    assert "name_receiver" not in by_field
    assert "num_street" not in by_field
    assert "address_reference" not in by_field
