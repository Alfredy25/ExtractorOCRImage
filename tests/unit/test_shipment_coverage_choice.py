"""La colonia del envío sigue el domicilio devuelto al crear el destinatario."""

from app.models.shipping import CoverageItem
from app.views.shipment_window import preferred_coverage_index


def _item(colony: str) -> CoverageItem:
    return CoverageItem(
        postal_code="50000",
        colony=colony,
        municipality="TOLUCA",
        city="TOLUCA",
        state="ESTADO DE MEXICO",
        coverage_type="PAQUETEXPRESS",
    )


def test_preferred_coverage_matches_saved_colony():
    coverages = [_item("CENTRO"), _item("LA MERCED"), _item("REFORMA")]

    assert preferred_coverage_index(coverages, "la merced") == 1


def test_preferred_coverage_falls_back_to_first():
    coverages = [_item("CENTRO"), _item("REFORMA")]

    assert preferred_coverage_index(coverages, "OTRA") == 0
    assert preferred_coverage_index([], "CENTRO") == 0
