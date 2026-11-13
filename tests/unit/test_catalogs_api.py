"""Smoke de los cuatro catálogos del directorio."""

import pytest

from app.api import http_support, job_roles_api, organizations_api, titles_api, volantes_api


def _audit() -> dict:
    return {
        "created_at": "2026-11-10T23:00:00Z",
        "updated_at": "2026-11-10T23:00:00Z",
        "created_by": 1,
        "updated_by": None,
    }


def _install(monkeypatch, responder):
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
            status, body = responder(method)
            return http_support.httpx.Response(status, json=body)

    monkeypatch.setattr(http_support.httpx, "Client", FakeClient)
    return captured


def _page(item: dict) -> dict:
    return {
        "page": 1,
        "page_size": 20,
        "total": 1,
        "total_pages": 1,
        "has_prev": False,
        "has_next": False,
        "search": "DIR",
        "items": [item],
    }


@pytest.mark.parametrize(
    ("list_fn", "create_fn", "conflict", "endpoint", "item", "payload"),
    [
        (
            titles_api.list_titles,
            titles_api.create_title,
            titles_api.TitlesConflictError,
            "/titles/",
            {"id": 1, "abbreviation": "DR.", "meaning": "Doctor"},
            {"abbreviation": "DR.", "meaning": "Doctor"},
        ),
        (
            job_roles_api.list_job_roles,
            job_roles_api.create_job_role,
            job_roles_api.JobRolesConflictError,
            "/job-roles/",
            {"id": 1, "abbreviation": "DIR.", "meaning": "Director"},
            {"abbreviation": "DIR.", "meaning": "Director"},
        ),
        (
            organizations_api.list_organizations,
            organizations_api.create_organization,
            organizations_api.OrganizationsConflictError,
            "/organizations/",
            {"id": 1, "name": "SAT", "state": "TABASCO"},
            {"name": "SAT", "state": "TABASCO"},
        ),
        (
            volantes_api.list_volantes,
            volantes_api.create_volante,
            volantes_api.VolantesConflictError,
            "/volante/",
            {"id": 1, "name": "VCS-26-131000-00167"},
            {"name": "VCS-26-131000-00167"},
        ),
    ],
)
def test_catalog_list_create_and_conflict(monkeypatch, list_fn, create_fn, conflict, endpoint, item, payload):
    body = {**item, **_audit()}

    def _ok(method):
        if method == "GET":
            return 200, _page(body)
        return 201, body

    captured = _install(monkeypatch, _ok)
    page = list_fn("token-ok", search="DIR")
    assert page.items[0].id == 1
    assert captured["url"].endswith(endpoint)
    assert captured["headers"]["Authorization"] == "Bearer token-ok"

    created = create_fn(payload, "token-ok")
    assert created.id == 1

    def _conflict(_method):
        return 409, {"detail": "ya existe"}

    _install(monkeypatch, _conflict)
    with pytest.raises(conflict):
        create_fn(payload, "token-ok")


def test_organizations_filter_by_state(monkeypatch):
    captured = _install(
        monkeypatch,
        lambda _method: (
            200,
            _page({"id": 1, "name": "SAT", "state": "TABASCO", **_audit()}),
        ),
    )

    organizations_api.list_organizations("token-ok", search="SAT", state="TABASCO")

    assert captured["params"]["state"] == "TABASCO"
    assert captured["params"]["search"] == "SAT"
