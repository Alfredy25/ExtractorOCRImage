"""Configuración central de la aplicación."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Modelo OpenAI (fijo)
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Timeout para llamadas API
TIMEOUT_SECONDS = int(os.getenv("TIMEOUT_SECONDS", "60"))

# Carpeta de exportaciones por defecto
EXPORT_DIR = os.getenv("EXPORT_DIR", str(Path(__file__).parent / "data" / "exports"))

# Rutas
APP_ROOT = Path(__file__).parent
DATA_DIR = APP_ROOT / "data"
DB_PATH = DATA_DIR / "db.sqlite3"
ASSETS_DIR = APP_ROOT / "assets"
ICONS_DIR = ASSETS_DIR / "icons"

# Sedes válidas
SEDES = ("AJUSCO", "COYOACÁN")

# Zoom
ZOOM_FACTOR = 1.25

# Reintentos IA
AI_RETRY_COUNT = 2


def get_db_engine() -> str:
    """Motor de BD: ``sqlite`` (por defecto) o ``mysql`` (lee ``DB_ENGINE`` en cada llamada)."""
    return os.getenv("DB_ENGINE", "sqlite").strip().lower()


def is_mysql() -> bool:
    return get_db_engine() == "mysql"


def get_mysql_config() -> dict:
    """Parámetros MySQL desde variables de entorno (sin credenciales en código)."""
    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": os.getenv("DB_USER", ""),
        "password": os.getenv("DB_PASSWORD", ""),
        "database": os.getenv("DB_NAME", "tools_OCR"),
        "charset": "utf8mb4",
    }


def get_db_summary_for_logs() -> str:
    """Texto seguro para logs (sin contraseña)."""
    if is_mysql():
        c = get_mysql_config()
        return f"MySQL {c['host']}:{c['port']}/{c['database']}"
    return f"SQLite {DB_PATH}"
