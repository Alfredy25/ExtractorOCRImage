"""Forzar SQLite en tests para no depender de MySQL aunque .env tenga DB_ENGINE=mysql."""
import pytest


@pytest.fixture(autouse=True)
def _force_sqlite_engine_for_tests(monkeypatch):
    monkeypatch.setenv("DB_ENGINE", "sqlite")
    # insert_extraction / list usan BD local en tests (sin servidor FastAPI).
    monkeypatch.setenv("OCR_USE_SQLITE_REPOSITORY", "1")
