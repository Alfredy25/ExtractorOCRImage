"""Tests del servicio de negocio Paquetexpress."""

from datetime import datetime

import pytest

from app.models.shipping import CoverageItem, ShippingDto
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

    assert draft["name_receiver"] == "Dr. Juan Perez Director General"
    assert draft["street"] == "Av. Central 123"
    assert draft["phone"] == "5512345678"
    assert draft["email"] == "notificaciones@feuh.com.mx"
    assert draft["rfc"] == "XAXX-010101-000"
    assert draft["width"] == "24"
    assert draft["address_reference"] == "Puerta gris"
    assert draft["quantity"] == "1"
    assert draft["coverage_type"] == "PAQUETEXPRESS"
    assert draft["comments"].startswith("ENTREGAR EN OFICIALIA DE PARTES")


def test_build_shipment_draft_joins_name_and_cargo():
    ocr = _ocr_form_data()
    ocr["campos"]["cargo_dependencia"] = ""
    assert px.build_shipment_draft(ocr, _coverage())["name_receiver"] == "Dr. Juan Perez"

    ocr["campos"]["nombre_titulo"] = ""
    ocr["campos"]["cargo_dependencia"] = "Director General"
    assert px.build_shipment_draft(ocr, _coverage())["name_receiver"] == "Director General"

    ocr["campos"]["nombre_titulo"] = ""
    ocr["campos"]["cargo_dependencia"] = ""
    assert px.build_shipment_draft(ocr, _coverage())["name_receiver"] == ""


def test_build_shipment_draft_uses_default_phone_when_contacto_empty():
    ocr = _ocr_form_data()
    ocr["campos"]["contacto"] = ""
    draft = px.build_shipment_draft(ocr, _coverage())

    assert draft["phone"] == "55 7586 8462"


def test_validate_shipment_form_accumulates_errors():
    draft = px.build_shipment_draft(_ocr_form_data(), _coverage())
    draft.update({
        "name_receiver": "x",
        "phone": "123",
        "postal_code": "A1030",
    })

    errors = px.validate_shipment_form(draft)
    fields = {error["campo"] for error in errors}

    assert {"Destinatario", "Teléfono", "Código Postal"} <= fields


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
    assert captured["payload"]["weight"] == "0.50"
    assert captured["payload"]["comments"] == draft["comments"]


def test_create_shipment_omits_empty_comments(monkeypatch):
    captured: dict = {}

    monkeypatch.setattr(px, "get_access_token", lambda: "token-ok")
    monkeypatch.setattr(
        px, "api_create_shipment", lambda payload, token: captured.update(payload) or {}
    )

    draft = px.build_shipment_draft(_ocr_form_data(), _coverage())
    draft["num_street"] = "12"
    draft["comments"] = "   "

    px.create_shipment(draft)

    assert "comments" not in captured


def test_get_coverages_for_postal_code_maps_not_found(monkeypatch):
    monkeypatch.setattr(px, "get_access_token", lambda: "token-ok")

    def _raise_not_found(_postal_code, _token):
        raise px.CoverageNotFoundError("no hay cobertura")

    monkeypatch.setattr(px, "get_coverages", _raise_not_found)

    with pytest.raises(px.PaquetexpressCoverageNotFoundError, match="no hay cobertura"):
        px.get_coverages_for_postal_code("01030")


def _valid_update_form() -> dict:
    draft = px.build_shipment_draft(_ocr_form_data(), _coverage())
    draft["num_street"] = "12"
    draft["email"] = "destinatario@example.com"
    return draft


def _shipping_dto() -> ShippingDto:
    return ShippingDto.model_validate({
        "id_shipping": 10,
        "id_folio": 19,
        "name_receiver": "DR. JUAN PEREZ",
        "rfc": "XAXX010101000",
        "country": "MEXICO",
        "state": "CIUDAD DE MEXICO",
        "city": "CIUDAD DE MEXICO",
        "colony": "FLORIDA",
        "street": "AV CENTRAL 123",
        "num_street": "12",
        "postal_code": "01030",
        "email": "destinatario@example.com",
        "phone": "5512345678",
        "address_reference": "Puerta gris",
        "quantity": 1,
        "package_code": 1,
        "content": "DOCUMENTOS LEGALES",
        "weight": "0.50",
        "length": "30.00",
        "width": "24.00",
        "height": "1.00",
        "coverage_type": "PAQUETEXPRESS",
        "comments": "ENTREGAR EN OFICIALIA",
        "created_at": datetime(2026, 8, 11, 18, 1, 12),
    })


def test_update_shipment_validates_before_http(monkeypatch):
    called = {"api": False}
    monkeypatch.setattr(px, "get_access_token", lambda: "token-ok")
    monkeypatch.setattr(
        px,
        "api_update_shipment",
        lambda *_args, **_kwargs: called.update(api=True),
    )

    with pytest.raises(px.PaquetexpressValidationError):
        px.update_shipment(10, {"name_receiver": "x"})

    assert called["api"] is False


def test_update_shipment_serializes_coverage_fields(monkeypatch):
    captured: dict = {}
    updated = _shipping_dto()

    monkeypatch.setattr(px, "get_access_token", lambda: "token-ok")

    def _fake_update(id_shipping, payload, token):
        captured["id_shipping"] = id_shipping
        captured["payload"] = payload
        captured["token"] = token
        return updated

    monkeypatch.setattr(px, "api_update_shipment", _fake_update)

    result = px.update_shipment(10, _valid_update_form())

    assert result is updated
    assert captured["id_shipping"] == 10
    assert captured["token"] == "token-ok"
    assert captured["payload"]["coverage_type"] == "PAQUETEXPRESS"
    assert captured["payload"]["state"] == "CIUDAD DE MEXICO"
    assert captured["payload"]["city"] == "CIUDAD DE MEXICO"
    assert captured["payload"]["colony"] == "FLORIDA"
    assert captured["payload"]["postal_code"] == "01030"
    assert captured["payload"]["weight"] == "0.50"
    assert "id_shipping" not in captured["payload"]
    assert "created_at" not in captured["payload"]


def test_update_shipment_maps_session_expired(monkeypatch):
    monkeypatch.setattr(px, "get_access_token", lambda: "token-ok")

    def _raise_expired(_id, _payload, _token):
        raise px.ShipmentsSessionExpiredError("expired")

    monkeypatch.setattr(px, "api_update_shipment", _raise_expired)

    with pytest.raises(px.PaquetexpressSessionExpiredError, match="expired"):
        px.update_shipment(10, _valid_update_form())


def test_update_shipment_maps_api_error(monkeypatch):
    monkeypatch.setattr(px, "get_access_token", lambda: "token-ok")

    def _raise_api(_id, _payload, _token):
        raise px.ShipmentsApiError("falló el backend")

    monkeypatch.setattr(px, "api_update_shipment", _raise_api)

    with pytest.raises(px.PaquetexpressServiceError, match="falló el backend"):
        px.update_shipment(10, _valid_update_form())


def test_list_shipments_by_date_range_forwards_my_shipments_false(monkeypatch):
    captured: dict = {}
    monkeypatch.setattr(px, "get_access_token", lambda: "token-ok")

    def _fake_list(desde, hasta, token, my_shipments=False):
        captured["desde"] = desde
        captured["hasta"] = hasta
        captured["token"] = token
        captured["my_shipments"] = my_shipments
        return []

    monkeypatch.setattr(px, "list_by_date_range", _fake_list)

    start = datetime(2026, 9, 1, 8, 0)
    end = datetime(2026, 9, 9, 18, 0)
    rows = px.list_shipments_by_date_range(start, end)

    assert rows == []
    assert captured["token"] == "token-ok"
    assert captured["desde"] == start
    assert captured["hasta"] == end
    assert captured["my_shipments"] is False


def test_list_shipments_by_date_range_forwards_my_shipments_true(monkeypatch):
    captured: dict = {}
    monkeypatch.setattr(px, "get_access_token", lambda: "token-ok")

    def _fake_list(_desde, _hasta, _token, my_shipments=False):
        captured["my_shipments"] = my_shipments
        return [_shipping_dto()]

    monkeypatch.setattr(px, "list_by_date_range", _fake_list)

    rows = px.list_shipments_by_date_range(
        datetime(2026, 9, 1), datetime(2026, 9, 9), my_shipments=True
    )

    assert captured["my_shipments"] is True
    assert len(rows) == 1
    assert rows[0].id_shipping == 10


def _audit() -> dict:
    return {
        "created_at": "2026-11-10T16:00:00",
        "updated_at": "2026-11-10T16:00:00",
        "created_by": 1,
        "updated_by": None,
    }


def _address(**overrides):
    from app.models.receiver import AddressDto

    data = {
        "id": 10,
        "street": "AV. REFORMA",
        "num_street": "120",
        "colony": "OTRA COLONIA",
        "municipality": "GUADALAJARA",
        "city": "GUADALAJARA",
        "state": "JALISCO",
        "postal_code": "44100",
        "country": "MEXICO",
        "address_reference": "FRENTE AL PARQUE",
        "receiver_id": 1,
        **_audit(),
    }
    data.update(overrides)
    return AddressDto.model_validate(data)


def _receiver(**overrides):
    from app.models.receiver import ReceiverDto

    data = {
        "id": 1,
        "type_entity": "PERSONA",
        "title": {"id": 3, "abbreviation": "DR.", "meaning": "Doctor", **_audit()},
        "full_name": "JUAN PEREZ LOPEZ",
        "email": "juan.perez@ejemplo.com",
        "position": None,
        "addresses": [],
        "contacts": [
            {
                "id": 6,
                "phone": "3312345678",
                "ext": "12",
                "id_destinatario": 1,
                **_audit(),
            }
        ],
        "volantes": [],
        **_audit(),
    }
    data.update(overrides)
    return ReceiverDto.model_validate(data)


def test_build_shipment_payload_uses_persona_title_and_coverage_colony():
    payload = px.build_shipment_payload_from_receiver(
        _receiver(),
        _address(),
        _coverage(),
        {"rfc": "XAXX-010101-000", "quantity": 1, "comments": "ENTREGAR EN RECEPCION"},
    )

    assert payload["name_receiver"] == "DR. JUAN PEREZ LOPEZ"
    assert payload["colony"] == "FLORIDA"
    assert payload["postal_code"] == "01030"
    assert payload["state"] == "CIUDAD DE MEXICO"
    assert payload["city"] == "CIUDAD DE MEXICO"
    assert payload["coverage_type"] == "PAQUETEXPRESS"
    assert payload["street"] == "AV. REFORMA"
    assert payload["phone"] == "3312345678"
    assert payload["email"] == "notificaciones@feuh.com.mx"
    assert payload["rfc"] == "XAXX-010101-000"


def test_build_shipment_payload_persona_joins_title_role_and_organization():
    receiver = _receiver(
        title={"id": 3, "abbreviation": "M. EN A.P.", "meaning": "Maestro", **_audit()},
        full_name="SONIA ISELA DIAZ MANJARREZ",
        position={
            "id": 8,
            "job_role": {
                "id": 2,
                "abbreviation": "CONT. GRAL. GUB.",
                "meaning": "Contadora General Gubernamental",
                **_audit(),
            },
            "organization": {
                "id": 4,
                "name": "SECRETARIA",
                "state": "MEXICO",
                **_audit(),
            },
            **_audit(),
        },
    )

    payload = px.build_shipment_payload_from_receiver(
        receiver, _address(), _coverage(), {"rfc": "XAXX-010101-000"}
    )

    assert payload["name_receiver"] == (
        "M. EN A.P. SONIA ISELA DIAZ MANJARREZ / CONT. GRAL. GUB. EN SECRETARIA"
    )


def test_build_shipment_payload_persona_name_stops_at_80_characters():
    receiver = _receiver(
        title={"id": 3, "abbreviation": "M. EN A.P.", "meaning": "Maestro", **_audit()},
        full_name="SONIA ISELA DIAZ MANJARREZ",
        position={
            "id": 8,
            "job_role": {
                "id": 2,
                "abbreviation": "CONT. GRAL. GUB.",
                "meaning": "Contadora",
                **_audit(),
            },
            "organization": {
                "id": 4,
                "name": "SECRETARIA DE FINANZAS DEL GOBIERNO DEL ESTADO DE MEXICO",
                "state": "MEXICO",
                **_audit(),
            },
            **_audit(),
        },
    )

    payload = px.build_shipment_payload_from_receiver(
        receiver, _address(), _coverage(), {}
    )

    assert len(payload["name_receiver"]) == 80
    assert payload["name_receiver"].startswith(
        "M. EN A.P. SONIA ISELA DIAZ MANJARREZ / CONT. GRAL. GUB. EN "
    )


def test_build_shipment_payload_gobierno_truncates_name_and_skips_short_phone():
    organization = {
        "id": 4,
        "name": "O" * 90,
        "state": "TABASCO",
        **_audit(),
    }
    receiver = _receiver(
        type_entity="GOBIERNO",
        title=None,
        full_name=None,
        email=None,
        position={
            "id": 8,
            "job_role": None,
            "organization": organization,
            **_audit(),
        },
        contacts=[
            {
                "id": 6,
                "phone": "331234567",
                "ext": None,
                "id_destinatario": 1,
                **_audit(),
            }
        ],
    )

    payload = px.build_shipment_payload_from_receiver(
        receiver,
        _address(address_reference=None),
        _coverage(),
        {"content": "DOCUMENTOS LEGALES"},
    )

    assert payload["name_receiver"] == "O" * 80
    assert len(payload["name_receiver"]) == 80
    assert payload["phone"] is None
    assert payload["email"] == "notificaciones@feuh.com.mx"
    assert payload["address_reference"] is None
    assert payload["content"] == "DOCUMENTOS LEGALES"


def test_build_shipment_payload_uses_form_email_not_receiver_email():
    payload = px.build_shipment_payload_from_receiver(
        _receiver(),
        _address(),
        _coverage(),
        {"email": "operacion@feuh.com.mx"},
    )

    assert payload["email"] == "operacion@feuh.com.mx"


def test_build_shipment_payload_uses_selected_contact_not_first():
    receiver = _receiver(
        contacts=[
            {
                "id": 6,
                "phone": "3312345678",
                "ext": "12",
                "id_destinatario": 1,
                **_audit(),
            },
            {
                "id": 7,
                "phone": "5511112222",
                "ext": "90",
                "id_destinatario": 1,
                **_audit(),
            },
        ]
    )

    payload = px.build_shipment_payload_from_receiver(
        receiver,
        _address(),
        _coverage(),
        {},
        contact=receiver.contacts[1],
    )

    assert payload["phone"] == "5511112222"
