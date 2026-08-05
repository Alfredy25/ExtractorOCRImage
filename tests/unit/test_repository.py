"""Tests del servicio de registros en modo API-only."""

from datetime import date, datetime, time

import pytest

from app.api.registros_api import RegistrosApiError, RegistrosSessionExpiredError
from app.services import registros_service as repo


def _sample_record() -> dict:
    return {
        "sede": "COYOACÁN",
        "nombre_imagen": "test.jpg",
        "destinatario_raw": "TEXTO",
        "nombre_o_titulo": "Juan",
        "cargo_dependencia": None,
        "direccion": "",
        "colonia": "ILEGIBLE",
        "municipio_o_alcaldia": None,
        "estado": "CDMX",
        "codigo_postal": None,
        "extras": None,
        "contacto": None,
        "indicaciones": None,
        "observaciones_ia": "Sin observaciones",
        "crop_x": 0,
        "crop_y": 0,
        "crop_w": 100,
        "crop_h": 100,
        "rotation_deg": 0,
        "aspect_mode": "FREE",
    }


def test_insert_extraction_calls_api_with_normalized_payload(monkeypatch):
    captured: dict = {}

    monkeypatch.setattr(repo, "get_access_token", lambda: "token-ok")

    def _fake_create_registro(payload, token):
        captured["payload"] = payload
        captured["token"] = token
        return 123

    monkeypatch.setattr(repo, "create_registro", _fake_create_registro)

    row_id = repo.insert_extraction(_sample_record())

    assert row_id == 123
    assert captured["token"] == "token-ok"
    assert captured["payload"]["sede"] == "COYOACAN"
    assert captured["payload"]["nombre_imagen"] == "TEST.JPG"
    assert captured["payload"]["nombre_o_titulo"] == "JUAN"
    assert captured["payload"]["direccion"] is None


def test_list_by_date_range_calls_api_with_expected_query(monkeypatch):
    day = date(2026, 4, 22)
    start = datetime.combine(day, time(8, 30, 15))
    end = datetime.combine(day, time(18, 5, 50))
    expected = [{"id": 1, "sede": "AJUSCO"}]
    captured: dict = {}

    monkeypatch.setattr(repo, "get_access_token", lambda: "token-ok")

    def _fake_list_registros(params, token):
        captured["params"] = params
        captured["token"] = token
        return expected

    monkeypatch.setattr(repo, "list_registros", _fake_list_registros)

    rows = repo.list_by_date_range(start, end, "COYOACÁN")

    assert rows == expected
    assert captured["token"] == "token-ok"
    assert captured["params"]["fecha_inicio"] == "2026-04-22T08:30:15"
    assert captured["params"]["fecha_fin"] == "2026-04-22T18:05:50"
    assert captured["params"]["sede"] == "COYOACAN"


def test_insert_extraction_raises_session_expired(monkeypatch):
    monkeypatch.setattr(repo, "get_access_token", lambda: "token-ok")

    def _raise_session_expired(_payload, _token):
        raise RegistrosSessionExpiredError("sesion expirada")

    monkeypatch.setattr(repo, "create_registro", _raise_session_expired)

    with pytest.raises(repo.RepositorySessionExpiredError):
        repo.insert_extraction(_sample_record())


def test_list_by_date_range_raises_api_error_on_network_failure(monkeypatch):
    monkeypatch.setattr(repo, "get_access_token", lambda: "token-ok")

    def _raise_api_error(_params, _token):
        raise RegistrosApiError("fallo de red")

    monkeypatch.setattr(repo, "list_registros", _raise_api_error)

    with pytest.raises(repo.RepositoryApiError):
        repo.list_by_date_range(datetime(2026, 1, 1), datetime(2026, 1, 2), "AJUSCO")
