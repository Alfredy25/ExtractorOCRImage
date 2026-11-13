"""Tests del alta de contacto."""

import pytest

from app.api import contacts_api
from app.models.receiver import ContactDto
from app.services import contacts_service as cs


def test_create_contact_sends_digits(monkeypatch):
    captured: dict = {}

    def _fake(receiver_id, payload, token):
        captured["id"] = receiver_id
        captured["payload"] = payload
        captured["token"] = token
        return ContactDto.model_validate({
            "id": 9,
            "phone": payload["phone"],
            "ext": payload.get("ext"),
            "id_destinatario": receiver_id,
            "created_at": "2026-11-10T16:00:00",
            "updated_at": "2026-11-10T16:00:00",
            "created_by": 1,
            "updated_by": None,
        })

    monkeypatch.setattr(cs, "get_access_token", lambda: "token-ok")
    monkeypatch.setattr(cs.contacts_api, "create_contact", _fake)

    created = cs.create_contact(4, {"phone": "55 1234 5678", "ext": "12"})

    assert created.id == 9
    assert captured["payload"] == {"phone": "5512345678", "ext": "12"}


def test_create_contact_wraps_duplicate(monkeypatch):
    monkeypatch.setattr(cs, "get_access_token", lambda: "token-ok")

    def _boom(_receiver_id, _payload, _token):
        raise contacts_api.ContactDuplicateError()

    monkeypatch.setattr(cs.contacts_api, "create_contact", _boom)

    with pytest.raises(cs.ContactDuplicateError):
        cs.create_contact(4, {"phone": "5512345678"})


def _original(**overrides) -> ContactDto:
    data = {
        "id": 9,
        "phone": "2288418600",
        "ext": None,
        "id_destinatario": 4,
        "created_at": "2026-11-10T16:00:00",
        "updated_at": "2026-11-10T16:00:00",
        "created_by": 1,
        "updated_by": None,
    }
    data.update(overrides)
    return ContactDto.model_validate(data)


def test_update_contact_sends_only_new_ext(monkeypatch):
    captured: dict = {}

    def _fake(contact_id, payload, token):
        captured["id"] = contact_id
        captured["payload"] = payload
        captured["token"] = token
        return _original(ext=payload["ext"])

    monkeypatch.setattr(cs, "get_access_token", lambda: "token-ok")
    monkeypatch.setattr(cs.contacts_api, "patch_contact", _fake)

    updated = cs.update_contact(9, {"phone": "2288418600", "ext": "15"}, _original())

    assert updated.ext == "15"
    assert captured["id"] == 9
    assert captured["payload"] == {"ext": "15"}


def test_update_contact_clears_ext_with_null(monkeypatch):
    captured: dict = {}

    def _fake(_contact_id, payload, _token):
        captured["payload"] = payload
        return _original(ext=None)

    monkeypatch.setattr(cs, "get_access_token", lambda: "token-ok")
    monkeypatch.setattr(cs.contacts_api, "patch_contact", _fake)

    cs.update_contact(9, {"phone": "2288418600", "ext": ""}, _original(ext="12"))

    assert captured["payload"] == {"ext": None}


def test_update_contact_skips_http_when_nothing_changed(monkeypatch):
    def _fail(*_args, **_kwargs):
        raise AssertionError("no debía llamar al API")

    monkeypatch.setattr(cs.contacts_api, "patch_contact", _fail)

    updated = cs.update_contact(
        9,
        {"phone": "228 841 8600", "ext": ""},
        _original(),
    )

    assert updated.id == 9
    assert updated.phone == "2288418600"
