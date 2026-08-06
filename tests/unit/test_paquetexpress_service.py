"""Tests del servicio de negocio Paquetexpress."""

import pytest

from app.models.shipping import CoverageItem
from app.services import paquetexpress_service as px


def _ocr_form_data() -> dict:
    return {
        "destinatario_raw": "texto",
        "campos": {
            "nombre_titulo": "Dr. Juan Perez",
            "cargo_dependencia": "Director General",
            "direccion": "Av. Central 123",
            "contacto": "5512345678",
            "indicaciones": "Puerta gris",
            "codigo_postal": "01030",
            "estado": "CDMX",
            "municipio_alcaldia": "ALVARO OBREGON",
            "colonia": "FLORIDA",
        },
        "observaciones_ia": "",
    }


def _coverage() -> CoverageItem:
    return CoverageItem(
        postal_code="01030",
        colony="FLORIDA",
        municipality="ALVARO OBREGON",
        city="CIUDAD DE MEXICO",
        state="CIUDAD DE MEXICO",
        coverage_type="PAQUETEXPRESS",
    )


def test_build_shipment_draft_uses_ocr_and_defaults():
    draft = px.build_shipment_draft(_ocr_form_data(), _coverage())

    assert draft["name_receiver"] == "Dr. Juan Perez"
    assert draft["street"] == "Av. Central 123"
    assert draft["phone"] == "5512345678"
    assert draft["address_reference"] == "Puerta gris"
    assert draft["quantity"] == "1"
    assert draft["coverage_type"] == "PAQUETEXPRESS"


def test_validate_shipment_form_accumulates_errors():
    draft = px.build_shipment_draft(_ocr_form_data(), _coverage())
    draft.update({
        "name_receiver": "x",
        "phone": "123",
        "postal_code": "A1030",
    })

    errors = px.validate_shipment_form(draft)
    fields = {error["campo"] for error in errors}

    assert {"name_receiver", "phone", "postal_code"} <= fields


def test_create_shipment_serializes_payload(monkeypatch):
    captured: dict = {}

    monkeypatch.setattr(px, "get_access_token", lambda: "token-ok")

    def _fake_create(payload, token):
        captured["payload"] = payload
        captured["token"] = token
        return {"ok": True, "shipment_id": 90}

    monkeypatch.setattr(px, "api_create_shipment", _fake_create)

    draft = px.build_shipment_draft(_ocr_form_data(), _coverage())
    draft["num_street"] = "12"
    draft["email"] = "destinatario@example.com"

    response = px.create_shipment(draft)

    assert response["ok"] is True
    assert captured["token"] == "token-ok"
    assert captured["payload"]["state"] == "CIUDAD DE MEXICO"
    assert captured["payload"]["city"] == "CIUDAD DE MEXICO"
    assert captured["payload"]["colony"] == "FLORIDA"
    assert captured["payload"]["postal_code"] == "01030"
    assert captured["payload"]["weight"] == "1.00"


def test_get_coverages_for_postal_code_maps_not_found(monkeypatch):
    monkeypatch.setattr(px, "get_access_token", lambda: "token-ok")

    def _raise_not_found(_postal_code, _token):
        raise px.CoverageNotFoundError("no hay cobertura")

    monkeypatch.setattr(px, "get_coverages", _raise_not_found)

    with pytest.raises(px.PaquetexpressCoverageNotFoundError, match="no hay cobertura"):
        px.get_coverages_for_postal_code("01030")
