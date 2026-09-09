"""Tests del contrato HTTP para creación de envíos Paquetexpress."""

from datetime import datetime

import pytest

from app.api import shipments_api


def _valid_payload() -> dict:
    return {
        "name_receiver": "DR. PEPE PINEDO PINEDO",
        "rfc": "XAXX010101000",
        "country": "MEXICO",
        "state": "CIUDAD DE MEXICO",
        "city": "CIUDAD DE MEXICO",
        "colony": "FLORIDA",
        "street": "CTO. CERRO DEL GATO",
        "num_street": "123",
        "postal_code": "01030",
        "quantity": 1,
        "package_code": 1,
        "content": "DOCUMENTOS LEGALES",
        "weight": "1.00",
        "length": "30.00",
        "width": "20.00",
        "height": "1.00",
        "coverage_type": "PAQUETEXPRESS",
    }


def test_create_shipment_posts_expected_payload(monkeypatch):
    captured: dict = {}

    class FakeClient:
        def __init__(self, timeout):
            captured["timeout"] = timeout

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def post(self, url, headers, json):
            captured["url"] = url
            captured["headers"] = headers
            captured["json"] = json
            return shipments_api.httpx.Response(200, json={"shipment_id": 88})

    monkeypatch.setattr(shipments_api.httpx, "Client", FakeClient)

    response = shipments_api.create_shipment(_valid_payload(), "token-ok")

    assert response["shipment_id"] == 88
    assert captured["url"].endswith("/shipments-px/")
    assert captured["headers"]["Authorization"] == "Bearer token-ok"
    assert captured["json"]["postal_code"] == "01030"


def test_create_shipment_raises_backend_error(monkeypatch):
    class FakeClient:
        def __init__(self, timeout):
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def post(self, _url, headers, json):
            assert headers["Authorization"] == "Bearer token-ok"
            assert json["postal_code"] == "01030"
            return shipments_api.httpx.Response(422, json={"detail": "payload inválido"})

    monkeypatch.setattr(shipments_api.httpx, "Client", FakeClient)

    with pytest.raises(shipments_api.ShipmentsApiError, match="payload inválido"):
        shipments_api.create_shipment(_valid_payload(), "token-ok")


def test_create_shipment_raises_session_expired(monkeypatch):
    class FakeClient:
        def __init__(self, timeout):
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def post(self, _url, headers, json):
            assert headers["Authorization"] == "Bearer token-ok"
            assert json["postal_code"] == "01030"
            return shipments_api.httpx.Response(401, json={"detail": "unauthorized"})

    monkeypatch.setattr(shipments_api.httpx, "Client", FakeClient)

    with pytest.raises(shipments_api.ShipmentsSessionExpiredError):
        shipments_api.create_shipment(_valid_payload(), "token-ok")


def _updated_dto_json() -> dict:
    return {
        "id_shipping": 10,
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
        "created_at": "2026-08-11T18:01:12",
    }


def test_update_shipment_posts_to_id_and_parses_dto(monkeypatch):
    captured: dict = {}

    class FakeClient:
        def __init__(self, timeout):
            captured["timeout"] = timeout

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def post(self, url, headers, json):
            captured["url"] = url
            captured["headers"] = headers
            captured["json"] = json
            return shipments_api.httpx.Response(200, json=_updated_dto_json())

    monkeypatch.setattr(shipments_api.httpx, "Client", FakeClient)

    result = shipments_api.update_shipment(10, _valid_payload(), "token-ok")

    assert result.id_shipping == 10
    assert result.colony == "FLORIDA"
    assert result.coverage_type == "PAQUETEXPRESS"
    assert captured["url"].endswith("/shipments-px/10")
    assert captured["headers"]["Authorization"] == "Bearer token-ok"
    assert captured["json"]["postal_code"] == "01030"


def test_update_shipment_raises_backend_error(monkeypatch):
    class FakeClient:
        def __init__(self, timeout):
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def post(self, _url, headers, json):
            assert headers["Authorization"] == "Bearer token-ok"
            return shipments_api.httpx.Response(422, json={"detail": "payload inválido"})

    monkeypatch.setattr(shipments_api.httpx, "Client", FakeClient)

    with pytest.raises(shipments_api.ShipmentsApiError, match="payload inválido"):
        shipments_api.update_shipment(10, _valid_payload(), "token-ok")


def test_update_shipment_raises_session_expired(monkeypatch):
    class FakeClient:
        def __init__(self, timeout):
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def post(self, _url, headers, json):
            return shipments_api.httpx.Response(401, json={"detail": "unauthorized"})

    monkeypatch.setattr(shipments_api.httpx, "Client", FakeClient)

    with pytest.raises(shipments_api.ShipmentsSessionExpiredError):
        shipments_api.update_shipment(10, _valid_payload(), "token-ok")


def _list_range_client(captured: dict, body, status: int = 200):
    class FakeClient:
        def __init__(self, timeout):
            captured["timeout"] = timeout

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def get(self, url, headers, params):
            captured["url"] = url
            captured["headers"] = headers
            captured["params"] = params
            return shipments_api.httpx.Response(status, json=body)

    return FakeClient


def test_list_by_date_range_sends_my_shipments_false(monkeypatch):
    captured: dict = {}
    monkeypatch.setattr(
        shipments_api.httpx, "Client", _list_range_client(captured, [])
    )
    start = datetime(2026, 9, 1, 8, 0)
    end = datetime(2026, 9, 9, 18, 0)

    rows = shipments_api.list_by_date_range(start, end, "token-ok")

    assert rows == []
    assert captured["url"].endswith("/shipments-px/")
    assert captured["headers"]["Authorization"] == "Bearer token-ok"
    assert captured["params"]["fecha_inicio"] == start
    assert captured["params"]["fecha_fin"] == end
    assert captured["params"]["my_shipments"] is False


def test_list_by_date_range_sends_my_shipments_true(monkeypatch):
    captured: dict = {}
    monkeypatch.setattr(
        shipments_api.httpx, "Client", _list_range_client(captured, [])
    )

    shipments_api.list_by_date_range(
        datetime(2026, 9, 1, 8, 0),
        datetime(2026, 9, 9, 18, 0),
        "token-ok",
        my_shipments=True,
    )

    assert captured["params"]["my_shipments"] is True


def test_list_by_date_range_parses_dto_list(monkeypatch):
    captured: dict = {}
    monkeypatch.setattr(
        shipments_api.httpx,
        "Client",
        _list_range_client(captured, [_updated_dto_json()]),
    )

    rows = shipments_api.list_by_date_range(
        datetime(2026, 8, 1), datetime(2026, 8, 31), "token-ok", my_shipments=False
    )

    assert len(rows) == 1
    assert rows[0].id_shipping == 10
    assert rows[0].colony == "FLORIDA"
    assert captured["params"]["my_shipments"] is False
