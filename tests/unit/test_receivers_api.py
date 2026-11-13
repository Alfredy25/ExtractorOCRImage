"""Tests del contrato HTTP de destinatarios."""

import pytest

from app.api import http_support, receivers_api


def _audit() -> dict:
    return {
        "created_at": "2026-11-10T16:00:00",
        "updated_at": "2026-11-10T16:00:00",
        "created_by": 1,
        "updated_by": None,
    }


def _receiver(receiver_id: int = 1) -> dict:
    audit = _audit()
    return {
        "id": receiver_id,
        "type_entity": "PERSONA",
        "title": {"id": 3, "abbreviation": "DR.", "meaning": "Doctor", **audit},
        "full_name": "JUAN PEREZ LOPEZ",
        "email": "juan.perez@ejemplo.com",
        "position": None,
        "addresses": [
            {
                "id": 10,
                "street": "AV. REFORMA",
                "num_street": "120",
                "colony": "CENTRO",
                "municipality": "GUADALAJARA",
                "city": "GUADALAJARA",
                "state": "JALISCO",
                "postal_code": "44100",
                "country": "MEXICO",
                "address_reference": None,
                "receiver_id": receiver_id,
                **audit,
            }
        ],
        "contacts": [],
        "volantes": [],
        **audit,
    }


def _page() -> dict:
    return {
        "page": 1,
        "page_size": 10,
        "total": 1,
        "total_pages": 1,
        "has_prev": False,
        "has_next": False,
        "order_by": "id",
        "direction": "asc",
        "search": "JUAN",
        "items": [_receiver()],
    }


def _install(monkeypatch, status: int, body):
    captured: dict = {}

    class FakeClient:
        def __init__(self, timeout):
            captured["timeout"] = timeout

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def request(self, method, url, headers=None, params=None, json=None):
            captured.update(method=method, url=url, headers=headers, params=params, json=json)
            return http_support.httpx.Response(status, json=body)

    monkeypatch.setattr(http_support.httpx, "Client", FakeClient)
    return captured


def test_search_receivers_sends_query(monkeypatch):
    captured = _install(monkeypatch, 200, _page())

    page = receivers_api.search_receivers("token-ok", search="Juan", page_size=10)

    assert page.total == 1
    assert page.items[0].full_name == "JUAN PEREZ LOPEZ"
    assert captured["method"] == "GET"
    assert captured["url"].endswith("/receivers/")
    assert captured["params"]["query"] == "Juan"
    assert captured["headers"]["Authorization"] == "Bearer token-ok"


def test_create_receiver_returns_dto(monkeypatch):
    captured = _install(monkeypatch, 201, _receiver(4))

    created = receivers_api.create_receiver({"type_entity": "PERSONA"}, "token-ok")

    assert created.id == 4
    assert captured["method"] == "POST"
    assert captured["json"] == {"type_entity": "PERSONA"}


def test_create_receiver_duplicate_exposes_id(monkeypatch):
    _install(
        monkeypatch,
        409,
        {"detail": {"msg": "El destinatario ya existe", "receiver_id": 7}},
    )

    with pytest.raises(receivers_api.ReceiverDuplicateError) as exc:
        receivers_api.create_receiver({}, "token-ok")

    assert exc.value.receiver_id == 7


def test_search_receivers_validation(monkeypatch):
    _install(
        monkeypatch,
        422,
        {"errors": [{"message": "Search debe tener al menos 3 caracteres", "field": "search", "type": "value_error"}]},
    )

    with pytest.raises(receivers_api.ReceiversValidationError) as exc:
        receivers_api.search_receivers("token-ok", search="ab")

    assert exc.value.errors[0]["field"] == "search"


def test_search_receivers_session_expired(monkeypatch):
    _install(monkeypatch, 401, {"detail": "Token inválido o expirado"})

    with pytest.raises(receivers_api.ReceiversSessionExpiredError):
        receivers_api.search_receivers("token-ok", search="Juan")


def test_patch_receiver_sends_changed_keys(monkeypatch):
    captured = _install(monkeypatch, 200, _receiver(1))

    updated = receivers_api.patch_receiver(
        1, {"full_name": "JUAN PEREZ GARCIA", "email": None}, "token-ok"
    )

    assert updated.id == 1
    assert captured["method"] == "PATCH"
    assert captured["url"].endswith("/receivers/1")
    assert captured["json"] == {"full_name": "JUAN PEREZ GARCIA", "email": None}


def test_patch_receiver_duplicate_exposes_id(monkeypatch):
    _install(
        monkeypatch,
        409,
        {"detail": {"msg": "El destinatario ya existe", "receiver_id": 8}},
    )

    with pytest.raises(receivers_api.ReceiverDuplicateError) as exc:
        receivers_api.patch_receiver(1, {"full_name": "OTRO"}, "token-ok")

    assert exc.value.receiver_id == 8


def test_add_volante_posts_name_to_receiver(monkeypatch):
    captured = _install(
        monkeypatch,
        201,
        {"id": 5, "name": "VCS-26-131000-00167", **_audit()},
    )

    created = receivers_api.add_volante(4, {"name": "VCS-26-131000-00167"}, "token-ok")

    assert created.id == 5
    assert created.name == "VCS-26-131000-00167"
    assert captured["method"] == "POST"
    assert captured["url"].endswith("/receivers/4/volantes")
    assert captured["json"] == {"name": "VCS-26-131000-00167"}


def test_add_volante_duplicate_exposes_id(monkeypatch):
    _install(
        monkeypatch,
        409,
        {"detail": {"msg": "El destinatario ya tiene ese volante", "volante_id": 5}},
    )

    with pytest.raises(receivers_api.ReceiverVolanteDuplicateError) as exc:
        receivers_api.add_volante(4, {"name": "VCS-26-131000-00167"}, "token-ok")

    assert exc.value.volante_id == 5


def test_patch_receiver_validation(monkeypatch):
    _install(
        monkeypatch,
        422,
        {"errors": [{"message": "El nombre no puede ser nulo", "field": "full_name", "type": "value_error"}]},
    )

    with pytest.raises(receivers_api.ReceiversValidationError) as exc:
        receivers_api.patch_receiver(1, {"full_name": None}, "token-ok")

    assert exc.value.errors[0]["field"] == "full_name"
