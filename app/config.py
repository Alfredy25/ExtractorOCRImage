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
