"""Tests del contrato HTTP de autenticación."""

import pytest

from app.api import auth_api


def test_authenticate_sends_email_and_password(monkeypatch):
    captured: dict = {}

    class FakeClient:
        def __init__(self, timeout):
            captured["timeout"] = timeout

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def post(self, url, json):
            captured["url"] = url
            captured["json"] = json
            return auth_api.httpx.Response(
                200,
                json={
                    "access_token": "token-ok",
                    "token_type": "bearer",
                },
            )

    monkeypatch.setattr(auth_api.httpx, "Client", FakeClient)

    token = auth_api.authenticate("  user@example.com  ", "a! 2?x")

    assert token == "token-ok"
    assert captured["json"] == {
        "email": "user@example.com",
        "password": "a! 2?x",
    }


def test_authenticate_rejects_empty_email():
    with pytest.raises(auth_api.AuthError, match="correo electrónico"):
        auth_api.authenticate(" ", "password_seguro")


@pytest.mark.parametrize(
    "email",
    [
        "no-es-un-correo",
        "usuario@",
        "@example.com",
        "usuario@example",
        "usuario @example.com",
    ],
)
def test_authenticate_rejects_invalid_email_without_http_request(
    monkeypatch,
    email,
):
    def fail_if_client_is_created(*_args, **_kwargs):
        pytest.fail("No debe realizarse una petición para un correo inválido")

    monkeypatch.setattr(auth_api.httpx, "Client", fail_if_client_is_created)

    with pytest.raises(auth_api.AuthError, match="correo electrónico válido"):
        auth_api.authenticate(email, "password_seguro")


@pytest.mark.parametrize("password", ["1", "12345", "a! 2?"])
def test_authenticate_rejects_short_password_without_http_request(
    monkeypatch,
    password,
):
    def fail_if_client_is_created(*_args, **_kwargs):
        pytest.fail("No debe realizarse una petición para una contraseña inválida")

    monkeypatch.setattr(auth_api.httpx, "Client", fail_if_client_is_created)

    with pytest.raises(auth_api.AuthError, match="al menos 6 caracteres"):
        auth_api.authenticate("user@example.com", password)
