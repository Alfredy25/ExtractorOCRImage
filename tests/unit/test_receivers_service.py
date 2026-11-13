"""Tests de armado y validación del alta de destinatarios."""

import pytest

from app.api import receivers_api
from app.models.receiver import Paginated, ReceiverDto, VolanteDto, validate_receiver
from app.services import receivers_service as rs


def _address(**overrides) -> dict:
    data = {
        "street": "Avenida Reforma",
        "num_street": "120",
        "colony": "Centro",
        "municipality": "Guadalajara",
        "city": "Guadalajara",
        "state": "Jalisco",
        "postal_code": "44100",
        "country": "Mexico",
        "address_reference": "Edificio norte",
    }
    data.update(overrides)
    return data


def _persona(**overrides) -> dict:
    data = {
        "type_entity": "PERSONA",
        "full_name": "juan perez lopez",
        "email": "Juan.Perez@Ejemplo.com",
        "title": {"abbreviation": "DR.", "meaning": "Doctor"},
        "organization": {"name": "Congreso del Estado", "state": "Tabasco"},
        "job_role": {"abbreviation": "DIR.", "meaning": "Director"},
        "address": _address(),
        "contact": {"phone": "33 1234 5678", "ext": "12"},
        "volante_name": "vcs-26-131000-00167",
    }
    data.update(overrides)
    return data


def test_build_persona_payload_normalizes_contact_and_state():
    payload = rs.build_receiver_payload(_persona())

    assert payload["type_entity"] == "PERSONA"
    assert payload["full_name"] == "juan perez lopez"
    assert payload["title"]["abbreviation"] == "DR."
    assert payload["position"]["organization"]["state"] == "Tabasco"
    assert payload["contact"] == {"phone": "3312345678", "ext": "12"}
    assert payload["volante"] == {"name": "VCS-26-131000-00167"}
    assert "address_reference" in payload["address"]


def test_build_gobierno_omits_name_and_title():
    payload = rs.build_receiver_payload(
        {
            "type_entity": "GOBIERNO",
            "full_name": "NO DEBE IR",
            "title": {"abbreviation": "LIC.", "meaning": "Licenciado"},
            "organization": {"name": "SAT", "state": "CIUDAD DE MEXICO"},
            "address": _address(address_reference=""),
            "volante_name": "",
        }
    )

    assert "full_name" not in payload
    assert "title" not in payload
    assert "volante" not in payload
    assert "address_reference" not in payload["address"]
    assert payload["position"]["organization"]["name"] == "SAT"
    assert "job_role" not in payload["position"]


def test_validate_receiver_accumulates_type_and_address_errors():
    payload = rs.build_receiver_payload(
        {
            "type_entity": "PERSONA",
            "full_name": "",
            "address": _address(street="A", num_street=""),
        }
    )
    model, errors = validate_receiver(payload)

    assert model is None
    campos = {item["campo"] for item in errors}
    assert "Nombre completo" in campos
    assert "Título" in campos
    assert "Calle" in campos
    assert "Número" in campos


def test_validate_receiver_normalizes_state_on_success():
    model, errors = validate_receiver(rs.build_receiver_payload(_persona()))

    assert errors == []
    assert model is not None
    dumped = model.model_dump(exclude_none=True)
    assert dumped["full_name"] == "JUAN PEREZ LOPEZ"
    assert dumped["address"]["state"] == "JALISCO"
    assert dumped["position"]["organization"]["state"] == "TABASCO"
    assert dumped["email"] == "Juan.Perez@ejemplo.com"


def test_create_receiver_sends_validated_body(monkeypatch):
    captured: dict = {}

    def _fake(payload, token):
        captured["payload"] = payload
        captured["token"] = token
        body = {
            "id": 1,
            "type_entity": "PERSONA",
            "title": {
                "id": 1,
                "abbreviation": "DR.",
                "meaning": "Doctor",
                "created_at": "2026-11-10T16:00:00",
                "updated_at": "2026-11-10T16:00:00",
                "created_by": 1,
                "updated_by": None,
            },
            "full_name": payload["full_name"],
            "email": payload["email"],
            "position": None,
            "addresses": [],
            "contacts": [],
            "volantes": [],
            "created_at": "2026-11-10T16:00:00",
            "updated_at": "2026-11-10T16:00:00",
            "created_by": 1,
            "updated_by": None,
        }
        return ReceiverDto.model_validate(body)

    monkeypatch.setattr(rs, "get_access_token", lambda: "token-ok")
    monkeypatch.setattr(rs.receivers_api, "create_receiver", _fake)

    created = rs.create_receiver(_persona(organization=None, job_role=None))

    assert created.full_name == "JUAN PEREZ LOPEZ"
    assert captured["token"] == "token-ok"
    assert captured["payload"]["address"]["state"] == "JALISCO"
    assert "position" not in captured["payload"]


def test_create_receiver_wraps_duplicate(monkeypatch):
    monkeypatch.setattr(rs, "get_access_token", lambda: "token-ok")

    def _boom(_payload, _token):
        raise receivers_api.ReceiverDuplicateError(9, "El destinatario ya existe")

    monkeypatch.setattr(rs.receivers_api, "create_receiver", _boom)

    with pytest.raises(rs.ReceiverDuplicateError) as exc:
        rs.create_receiver(_persona())

    assert exc.value.receiver_id == 9


def test_search_without_text_omits_query_and_keeps_page_size(monkeypatch):
    monkeypatch.setattr(rs, "get_access_token", lambda: "token-ok")
    monkeypatch.setattr(rs.receivers_api, "search_receivers", _empty_page)

    rs.search_receivers(
        "   ",
        type_entity="GOBIERNO",
        state="JALISCO",
        order_by="name_org",
        direction="asc",
    )

    assert _empty_page.kwargs["search"] is None
    assert _empty_page.kwargs["page_size"] == 10
    assert _empty_page.kwargs["type_entity"] == "GOBIERNO"
    assert _empty_page.kwargs["state"] == "JALISCO"


def test_search_rejects_short_text_without_http(monkeypatch):
    def _fail(*_args, **_kwargs):
        raise AssertionError("no debía llamar a la API")

    monkeypatch.setattr(rs.receivers_api, "search_receivers", _fail)

    with pytest.raises(rs.ReceiverValidationError):
        rs.search_receivers("ab")


def _empty_page(*_args, **kwargs):
    _empty_page.kwargs = kwargs
    return Paginated[ReceiverDto](
        page=kwargs.get("page", 1),
        page_size=kwargs.get("page_size", 10),
        total=0,
        total_pages=0,
        items=[],
    )


def test_search_uses_flow_defaults(monkeypatch):
    """El flujo arranca en página 1, 10 por página, id ascendente."""
    monkeypatch.setattr(rs, "get_access_token", lambda: "token-ok")
    monkeypatch.setattr(rs.receivers_api, "search_receivers", _empty_page)

    rs.search_receivers("Maria Fernanda")

    assert _empty_page.kwargs["page"] == 1
    assert _empty_page.kwargs["page_size"] == 10
    assert _empty_page.kwargs["order_by"] == "id"
    assert _empty_page.kwargs["direction"] == "asc"


def test_update_receiver_sends_only_changed_keys(monkeypatch):
    captured: dict = {}
    original = ReceiverDto.model_validate({
        "id": 1,
        "type_entity": "PERSONA",
        "title": {
            "id": 1,
            "abbreviation": "DR.",
            "meaning": "Doctor",
            "created_at": "2026-11-10T16:00:00",
            "updated_at": "2026-11-10T16:00:00",
            "created_by": 1,
            "updated_by": None,
        },
        "full_name": "JUAN PEREZ LOPEZ",
        "email": "juan.perez@ejemplo.com",
        "position": None,
        "addresses": [],
        "contacts": [],
        "volantes": [],
        "created_at": "2026-11-10T16:00:00",
        "updated_at": "2026-11-10T16:00:00",
        "created_by": 1,
        "updated_by": None,
    })

    def _fake(receiver_id, payload, token):
        captured["id"] = receiver_id
        captured["payload"] = payload
        captured["token"] = token
        return original.model_copy(update={"full_name": "JUAN PEREZ GARCIA", "email": None})

    monkeypatch.setattr(rs, "get_access_token", lambda: "token-ok")
    monkeypatch.setattr(rs.receivers_api, "patch_receiver", _fake)

    form = {
        "type_entity": "PERSONA",
        "full_name": "juan perez garcia",
        "email": "",
        "title": {"abbreviation": "DR.", "meaning": "Doctor"},
    }
    updated = rs.update_receiver(1, form, original)

    assert updated.full_name == "JUAN PEREZ GARCIA"
    assert captured["id"] == 1
    assert captured["payload"] == {
        "full_name": "JUAN PEREZ GARCIA",
        "email": None,
    }
    assert "type_entity" not in captured["payload"]
    assert "title" not in captured["payload"]
    assert "address" not in captured["payload"]
    assert "contact" not in captured["payload"]


def test_build_receiver_update_payload_omits_unchanged_identity():
    original = ReceiverDto.model_validate({
        "id": 1,
        "type_entity": "PERSONA",
        "title": {
            "id": 1,
            "abbreviation": "DR.",
            "meaning": "Doctor",
            "created_at": "2026-11-10T16:00:00",
            "updated_at": "2026-11-10T16:00:00",
            "created_by": 1,
            "updated_by": None,
        },
        "full_name": "JUAN PEREZ LOPEZ",
        "email": "juan.perez@ejemplo.com",
        "position": None,
        "addresses": [],
        "contacts": [],
        "volantes": [],
        "created_at": "2026-11-10T16:00:00",
        "updated_at": "2026-11-10T16:00:00",
        "created_by": 1,
        "updated_by": None,
    })
    payload = rs.build_receiver_update_payload(
        {
            "type_entity": "PERSONA",
            "full_name": "JUAN PEREZ LOPEZ",
            "email": "juan.perez@ejemplo.com",
            "title": {"abbreviation": "DR.", "meaning": "Doctor"},
        },
        original,
    )
    assert payload == {}


def test_search_forwards_paging_and_order(monkeypatch):
    monkeypatch.setattr(rs, "get_access_token", lambda: "token-ok")
    monkeypatch.setattr(rs.receivers_api, "search_receivers", _empty_page)

    rs.search_receivers(
        "Maria Fernanda",
        type_entity="GOBIERNO",
        state="JALISCO",
        page=3,
        page_size=25,
        order_by="full_name",
        direction="desc",
    )

    assert _empty_page.kwargs["type_entity"] == "GOBIERNO"
    assert _empty_page.kwargs["state"] == "JALISCO"
    assert _empty_page.kwargs["page"] == 3
    assert _empty_page.kwargs["page_size"] == 25
    assert _empty_page.kwargs["order_by"] == "full_name"
    assert _empty_page.kwargs["direction"] == "desc"


def test_add_volante_sends_uppercase_name(monkeypatch):
    captured: dict = {}

    def _fake(receiver_id, payload, token):
        captured["receiver_id"] = receiver_id
        captured["payload"] = payload
        captured["token"] = token
        return VolanteDto.model_validate({
            "id": 5,
            "name": payload["name"],
            "created_at": "2026-11-10T16:00:00",
            "updated_at": "2026-11-10T16:00:00",
            "created_by": 1,
            "updated_by": None,
        })

    monkeypatch.setattr(rs, "get_access_token", lambda: "token-ok")
    monkeypatch.setattr(rs.receivers_api, "add_volante", _fake)

    created = rs.add_volante(4, "  vcs-26-131000-00167  ")

    assert created.name == "VCS-26-131000-00167"
    assert captured["receiver_id"] == 4
    assert captured["payload"] == {"name": "VCS-26-131000-00167"}


def test_add_volante_rejects_short_name_without_http(monkeypatch):
    def _fail(*_args, **_kwargs):
        raise AssertionError("no debía llamar a la API")

    monkeypatch.setattr(rs.receivers_api, "add_volante", _fail)

    with pytest.raises(rs.ReceiverValidationError) as exc:
        rs.add_volante(4, "V-2026")

    assert exc.value.errors[0]["campo"] == "Volante"
