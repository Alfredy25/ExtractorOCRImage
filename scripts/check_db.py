#!/usr/bin/env python3
"""
Healthcheck de base de datos: SELECT 1 y consulta a extractions.

Uso (raíz del proyecto):
  python scripts/check_db.py

Respeta DB_ENGINE (.env): sqlite o mysql.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")


def main() -> int:
    from app.core.db_health import check_database

    ok, msg = check_database()
    print(msg)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
