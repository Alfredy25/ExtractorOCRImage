#!/usr/bin/env python3
"""
Aplica sql/schema_mysql.sql contra MySQL usando variables de entorno (.env).

Uso (desde la raíz del proyecto):
  python scripts/create_mysql_schema.py

Requiere: DB_ENGINE=mysql (opcional para este script; se conecta siempre a MySQL por env),
  DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
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
    import pymysql

    from app.config import get_mysql_config

    cfg = get_mysql_config()
    if not cfg.get("user"):
        print("Error: defina DB_USER (y credenciales) en .env", file=sys.stderr)
        return 1

    path = ROOT / "sql" / "schema_mysql.sql"
    if not path.is_file():
        print(f"Error: no existe {path}", file=sys.stderr)
        return 1

    raw = path.read_text(encoding="utf-8")
    stmts: list[str] = []
    for chunk in raw.split(";"):
        lines = []
        for line in chunk.splitlines():
            line = line.strip()
            if not line or line.startswith("--"):
                continue
            lines.append(line)
        s = " ".join(lines).strip()
        if s:
            stmts.append(s + ";")

    conn = pymysql.connect(
        host=cfg["host"],
        port=cfg["port"],
        user=cfg["user"],
        password=cfg["password"],
        database=cfg["database"],
        charset=cfg["charset"],
    )
    try:
        cur = conn.cursor()
        for stmt in stmts:
            cur.execute(stmt)
        conn.commit()
        cur.close()
        print(f"Esquema aplicado en {cfg['host']}:{cfg['port']}/{cfg['database']}")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
