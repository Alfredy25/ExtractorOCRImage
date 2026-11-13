"""DTO del catálogo SEPOMEX."""

from __future__ import annotations

from pydantic import BaseModel


class SepomexDto(BaseModel):
    """Asentamiento devuelto por ``GET /sepomex/{postal_code}``."""

    id: int
    postal_code: str
    settlement: str
    settlement_type: str
    municipality: str
    city: str | None = None
    state: str
    state_code: str
    zone: str
