"""Tests del contrato HTTP de domicilios."""

import pytest

from app.api import addresses_api, http_support


def _audit() -> dict:
    return {
        "created_at": "2026-11-10T16:00:00",
        "updated_at": "2026-11-10T16:00:00",
        "created_by": 1,
        "updated_by": None,
    }


def _address(address_id: int = 10, **overrides) -> dict:
    data = {
        "id": address_id,
        "street": "AV. REFORMA",
        "num_street": "120",
        "colony": "CENTRO",
        "municipality": "GUADALAJARA",
        "city": "GUADALAJARA",
        "state": "JALISCO",
        "postal_code": "44100",
        "country": "MEXICO",
        "address_reference": "FRENTE AL PARQUE",
        "receiver_id": 4,
        **_audit(),
    }
    data.update(overrides)
    return data


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


def test_create_address_posts_to_receiver(monkeypatch):
    captured = _install(monkeypatch, 201, _address(11))

    created = addresses_api.create_address(4, {"street": "AVENIDA REFORMA"}, "token-ok")

    assert created.id == 11
    assert captured["method"] == "POST"
    assert captured["url"].endswith("/addresses/4")


def test_patch_address_sends_street_and_reference(monkeypatch):
    captured = _install(
        monkeypatch,
        200,
        _address(10, num_street="122", address_reference="PLANTA BAJA"),
    )

    updated = addresses_api.patch_address(
        10,
        {"num_street": "122", "address_reference": "PLANTA BAJA"},
        "token-ok",
    )

    assert updated.num_street == "122"
    assert updated.address_reference == "PLANTA BAJA"
    assert captured["method"] == "PATCH"
    assert captured["url"].endswith("/addresses/10")
    assert captured["json"] == {"num_street": "122", "address_reference": "PLANTA BAJA"}


def test_patch_address_duplicate_exposes_id(monkeypatch):
    _install(
        monkeypatch,
        409,
        {"detail": {"msg": "El destinatario ya tiene un domicilio equivalente", "address_id": 3}},
    )

    with pytest.raises(addresses_api.AddressDuplicateError) as exc:
        addresses_api.patch_address(10, {"street": "OTRA"}, "token-ok")

    assert exc.value.address_id == 3
