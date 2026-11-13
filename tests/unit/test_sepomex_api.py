"""Tests del contrato HTTP de SEPOMEX."""

import pytest

from app.api import http_support, sepomex_api


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
            captured.update(method=method, url=url, headers=headers)
            return http_support.httpx.Response(status, json=body)

    monkeypatch.setattr(http_support.httpx, "Client", FakeClient)
    return captured


def test_get_sepomex_parses_list(monkeypatch):
    captured = _install(
        monkeypatch,
        200,
        [
            {
                "id": 1,
                "postal_code": "97000",
                "settlement": "CENTRO",
                "settlement_type": "Colonia",
                "municipality": "Mérida",
                "city": None,
                "state": "YUCATAN",
                "state_code": "31",
                "zone": "Urbano",
            }
        ],
    )

    rows = sepomex_api.get_sepomex("97000", "token-ok")

    assert rows[0].settlement == "CENTRO"
    assert rows[0].city is None
    assert captured["url"].endswith("/sepomex/97000")
    assert captured["headers"]["Authorization"] == "Bearer token-ok"


def test_get_sepomex_not_found(monkeypatch):
    _install(monkeypatch, 404, {"detail": "Código postal 97000 no existe en el catálogo"})

    with pytest.raises(sepomex_api.SepomexNotFoundError, match="97000"):
        sepomex_api.get_sepomex("97000", "token-ok")
