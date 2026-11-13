"""Tests de armado del PATCH de domicilio."""

from app.models.receiver import AddressDto
from app.services import addresses_service as ads


def _address_dto(**overrides) -> AddressDto:
    data = {
        "id": 10,
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
        "created_at": "2026-11-10T16:00:00",
        "updated_at": "2026-11-10T16:00:00",
        "created_by": 1,
        "updated_by": None,
    }
    data.update(overrides)
    return AddressDto.model_validate(data)


def test_update_address_sends_only_changed_keys(monkeypatch):
    captured: dict = {}
    original = _address_dto()

    def _fake(address_id, payload, token):
        captured["id"] = address_id
        captured["payload"] = payload
        captured["token"] = token
        return original.model_copy(update=payload)

    monkeypatch.setattr(ads, "get_access_token", lambda: "token-ok")
    monkeypatch.setattr(ads.addresses_api, "patch_address", _fake)

    form = {
        "street": "AV. REFORMA",
        "num_street": "122",
        "colony": "CENTRO",
        "municipality": "GUADALAJARA",
        "city": "GUADALAJARA",
        "state": "JALISCO",
        "postal_code": "44100",
        "country": "MEXICO",
        "address_reference": "PLANTA BAJA",
    }
    updated = ads.update_address(10, form, original)

    assert captured["id"] == 10
    assert captured["payload"] == {
        "num_street": "122",
        "address_reference": "PLANTA BAJA",
    }
    assert "street" not in captured["payload"]
    assert updated.num_street == "122"


def test_update_address_clears_reference_with_null(monkeypatch):
    captured: dict = {}
    original = _address_dto()

    def _fake(_address_id, payload, _token):
        captured["payload"] = payload
        return original.model_copy(update={"address_reference": None})

    monkeypatch.setattr(ads, "get_access_token", lambda: "token-ok")
    monkeypatch.setattr(ads.addresses_api, "patch_address", _fake)

    form = {
        "street": "AV. REFORMA",
        "num_street": "120",
        "colony": "CENTRO",
        "municipality": "GUADALAJARA",
        "city": "GUADALAJARA",
        "state": "JALISCO",
        "postal_code": "44100",
        "country": "MEXICO",
        "address_reference": "",
    }
    ads.update_address(10, form, original)

    assert captured["payload"] == {"address_reference": None}
