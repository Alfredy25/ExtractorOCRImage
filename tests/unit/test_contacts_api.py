"""Tests del contrato HTTP de contactos."""

import pytest

from app.api import contacts_api, http_support


def _contact(contact_id: int = 3) -> dict:
    return {
        "id": contact_id,
        "phone": "5512345678",
        "ext": "12",
        "id_destinatario": 4,
        "created_at": "2026-11-10T16:00:00",
        "updated_at": "2026-11-10T16:00:00",
        "created_by": 1,
        "updated_by": None,
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


def test_create_contact_posts_to_receiver(monkeypatch):
    captured = _install(monkeypatch, 201, _contact(9))

    created = contacts_api.create_contact(4, {"phone": "5512345678", "ext": "12"}, "token-ok")

    assert created.id == 9
    assert captured["method"] == "POST"
    assert captured["url"].endswith("/contacts/4")
    assert captured["json"] == {"phone": "5512345678", "ext": "12"}


def test_create_contact_duplicate_is_not_hard_error_shape(monkeypatch):
    _install(
        monkeypatch,
        409,
        {"detail": "El destinatario ya tiene un contacto con ese teléfono y extensión"},
    )

    with pytest.raises(contacts_api.ContactDuplicateError) as exc:
        contacts_api.create_contact(4, {"phone": "5512345678"}, "token-ok")

    assert "teléfono" in str(exc.value)
