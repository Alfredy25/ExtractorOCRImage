"""Tests del contrato HTTP de coberturas Paquetexpress."""

import pytest

from app.api import coverages_api


def test_get_coverages_calls_expected_url_and_headers(monkeypatch):
    captured: dict = {}

    class FakeClient:
        def __init__(self, timeout):
            captured["timeout"] = timeout

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def get(self, url, headers):
            captured["url"] = url
            captured["headers"] = headers
            return coverages_api.httpx.Response(
                200,
                json=[
                    {
                        "postal_code": "01030",
                        "colony": "FLORIDA",
                        "municipality": "ALVARO OBREGON",
                        "city": "CIUDAD DE MEXICO",
                        "state": "CIUDAD DE MEXICO",
                        "coverage_type": "PAQUETEXPRESS",
                    }
                ],
            )

    monkeypatch.setattr(coverages_api.httpx, "Client", FakeClient)

    rows = coverages_api.get_coverages("55010", "token-ok")

    assert len(rows) == 1
    assert rows[0]["colony"] == "FLORIDA"
    assert captured["url"].endswith("/coverages/55010")
    assert captured["headers"]["Authorization"] == "Bearer token-ok"


def test_get_coverages_raises_not_found(monkeypatch):
    class FakeClient:
        def __init__(self, timeout):
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def get(self, _url, headers):
            assert headers["Authorization"] == "Bearer token-ok"
            return coverages_api.httpx.Response(
                404,
                json={"detail": "no hay cobertura con el cp 55010 en el sistema"},
            )

    monkeypatch.setattr(coverages_api.httpx, "Client", FakeClient)

    with pytest.raises(coverages_api.CoverageNotFoundError, match="no hay cobertura"):
        coverages_api.get_coverages("55010", "token-ok")


def test_get_coverages_raises_session_expired(monkeypatch):
    class FakeClient:
        def __init__(self, timeout):
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def get(self, _url, headers):
            assert headers["Authorization"] == "Bearer token-ok"
            return coverages_api.httpx.Response(401, json={"detail": "unauthorized"})

    monkeypatch.setattr(coverages_api.httpx, "Client", FakeClient)

    with pytest.raises(coverages_api.CoveragesSessionExpiredError):
        coverages_api.get_coverages("55010", "token-ok")
