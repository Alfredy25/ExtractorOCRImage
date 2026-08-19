"""Persistencia local del último correo de login."""

from pathlib import Path

from app.utils import remembered_email as remembered


def test_save_and_load_remembered_email(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(remembered, "app_data_directory", lambda: tmp_path)

    remembered.save_remembered_email("  ana@empresa.com  ")

    assert remembered.load_remembered_email() == "ana@empresa.com"
    assert (tmp_path / "last_email.txt").read_text(encoding="utf-8") == (
        "ana@empresa.com\n"
    )


def test_load_remembered_email_missing_file(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(remembered, "app_data_directory", lambda: tmp_path)

    assert remembered.load_remembered_email() is None


def test_clear_remembered_email(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(remembered, "app_data_directory", lambda: tmp_path)
    remembered.save_remembered_email("ana@empresa.com")

    remembered.clear_remembered_email()

    assert remembered.load_remembered_email() is None
    assert not (tmp_path / "last_email.txt").exists()


def test_save_ignores_implausible_email(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(remembered, "app_data_directory", lambda: tmp_path)

    remembered.save_remembered_email("no-es-correo")
    remembered.save_remembered_email("con espacios@empresa.com")
    remembered.save_remembered_email("")

    assert remembered.load_remembered_email() is None
    assert not (tmp_path / "last_email.txt").exists()


def test_load_ignores_corrupt_file(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(remembered, "app_data_directory", lambda: tmp_path)
    (tmp_path / "last_email.txt").write_text("no-es-correo\n", encoding="utf-8")

    assert remembered.load_remembered_email() is None
