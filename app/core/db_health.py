"""Comprobaciones ligeras de conectividad y tabla extractions."""
from __future__ import annotations

from app.config import get_db_summary_for_logs
from app.core.repository import get_connection


def check_database() -> tuple[bool, str]:
    """
    SELECT 1 y conteo en ``extractions``.
    Devuelve (éxito, mensaje). No incluye secretos.
    """
    summary = get_db_summary_for_logs()
    try:
        with get_connection() as (conn, engine):
            if engine == "mysql":
                cur = conn.cursor()
                cur.execute("SELECT 1 AS ok")
                one = cur.fetchone()
                if not one or one.get("ok") != 1:
                    return False, f"{summary}: SELECT 1 inesperado"
                cur.execute("SELECT COUNT(*) AS n FROM extractions")
                n = cur.fetchone()["n"]
                cur.close()
            else:
                conn.execute("SELECT 1")
                cur = conn.execute("SELECT COUNT(*) FROM extractions")
                n = cur.fetchone()[0]
        return True, f"{summary}; extractions.n={n}"
    except Exception as e:
        return False, f"{summary}: {e}"
