"""Último correo de login, en el perfil local (sin contraseña ni JWT)."""

from __future__ import annotations

from pathlib import Path

from app.utils.paths import app_data_directory

_FILENAME = "last_email.txt"
_MAX_LEN = 254


def remembered_email_path() -> Path:
    """``%LOCALAPPDATA%\\ExtractorOCR\\last_email.txt``."""
    return app_data_directory() / _FILENAME


def load_remembered_email() -> str | None:
    """Devuelve el correo guardado, o None si no hay archivo válido."""
    path = remembered_email_path()
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return None
    email = raw.splitlines()[0].strip() if raw else ""
    return email if _is_plausible_email(email) else None


def save_remembered_email(email: str) -> None:
    """Persiste solo el correo tras un login correcto."""
    cleaned = (email or "").strip()
    if not _is_plausible_email(cleaned):
        return
    path = remembered_email_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(cleaned + "\n", encoding="utf-8")


def clear_remembered_email() -> None:
    """Olvida el correo guardado (casilla desmarcada tras login correcto)."""
    try:
        remembered_email_path().unlink(missing_ok=True)
    except OSError:
        return


def _is_plausible_email(email: str) -> bool:
    if not email or len(email) > _MAX_LEN:
        return False
    if any(ch.isspace() for ch in email):
        return False
    return "@" in email and "." in email.split("@")[-1]
