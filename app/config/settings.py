"""Configuración central de la aplicación."""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from app.config.constants import AI_RETRY_COUNT, SEDES, ZOOM_FACTOR

load_dotenv()

# Modelo OpenAI (fijo)
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Timeout para llamadas API (OpenAI)
TIMEOUT_SECONDS = int(os.getenv("TIMEOUT_SECONDS", "60"))

# --- Backend FastAPI (login JWT, CRUD registros OCR vía HTTP) ---
# URL base sin barra final; en desarrollo suele ser http://127.0.0.1:8000, en producción https://dominio
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
# Rutas relativas a API_BASE_URL (deben empezar por /)
LOGIN_ENDPOINT = os.getenv("LOGIN_ENDPOINT", "/auth/login")
REGISTROS_ENDPOINT = os.getenv("REGISTROS_ENDPOINT", "/registros/")
COVERTURAS_ENDPOINT = os.getenv("COVERTURAS_ENDPOINT", "/coverages/")
ENVIOS_PX_ENDPOINT = os.getenv("ENVIOS_PX_ENDPOINT", "/shipments-px/")
RECEIVERS_ENDPOINT = os.getenv("RECEIVERS_ENDPOINT", "/receivers/")
ADDRESSES_ENDPOINT = os.getenv("ADDRESSES_ENDPOINT", "/addresses/")
CONTACTS_ENDPOINT = os.getenv("CONTACTS_ENDPOINT", "/contacts/")
TITLES_ENDPOINT = os.getenv("TITLES_ENDPOINT", "/titles/")
JOB_ROLES_ENDPOINT = os.getenv("JOB_ROLES_ENDPOINT", "/job-roles/")
ORGANIZATIONS_ENDPOINT = os.getenv("ORGANIZATIONS_ENDPOINT", "/organizations/")
VOLANTES_ENDPOINT = os.getenv("VOLANTES_ENDPOINT", "/volante/")
SEPOMEX_ENDPOINT = os.getenv("SEPOMEX_ENDPOINT", "/sepomex/")
# TIMEOUT del cliente HTTP hacia FastAPI (login, POST/GET /registros), independiente del timeout de OpenAI
API_TIMEOUT_SECONDS = int(os.getenv("API_TIMEOUT_SECONDS", "60"))


def api_abs_url(path: str) -> str:
    """URL absoluta del backend: API_BASE_URL + path (path con o sin '/' inicial)."""
    p = path.strip()
    if not p.startswith("/"):
        p = "/" + p
    abs_url = f"{API_BASE_URL}{p}"
    print(f"abs_url: {abs_url}")
    return abs_url


def _resolve_app_root() -> Path:
    """Directorio ``app/`` en desarrollo y en el bundle de PyInstaller.

    Con ``--onedir``, los datos van a ``sys._MEIPASS`` (la carpeta ``_internal``).
    ``Path(__file__)`` no apunta a un archivo real cuando el código viaja en el
    archivo PYZ, así que las fuentes e imágenes hay que resolverlas desde ahí.
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "app"
    return Path(__file__).resolve().parent.parent


# Rutas
APP_ROOT = _resolve_app_root()
PROJECT_ROOT = APP_ROOT.parent
DATA_DIR = APP_ROOT / "data"
ASSETS_DIR = APP_ROOT / "assets"
ICONS_DIR = ASSETS_DIR / "icons"
IMAGES_DIR = ASSETS_DIR / "images"
THEMES_DIR = ASSETS_DIR / "themes"

# Carpeta de exportaciones por defecto
EXPORT_DIR = os.getenv("EXPORT_DIR", str(DATA_DIR / "exports"))
