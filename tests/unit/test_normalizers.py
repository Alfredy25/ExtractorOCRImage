"""Normalización de texto y el query que sale hacia los catálogos."""

import pytest
from pydantic import ValidationError

from app.models.receiver import JobRoleInput, TitleInput
from app.services import catalogs_service
from app.utils import normalizers as nz


def test_clean_base_text_order_keeps_periods_and_enie():
    assert nz.clean_base_text('  josé "pérez" - #1  ') == "JOSE PEREZ 1"
    assert nz.clean_base_text("DR. JOSÉ") == "DR. JOSE"
    assert nz.clean_base_text("niño") == "NIÑO"
    assert nz.clean_base_text("  müller  ") == "MULLER"
    assert nz.clean_base_text("") == ""


def test_full_name_does_not_abbreviate():
    assert nz.normalize_full_name("Dr. María López") == "DR. MARIA LOPEZ"


def test_long_phrase_wins_over_shorter_word():
    phrase = "Administradora Desconcentrada de Recaudación del Estado"
    assert nz.normalize_job_role(phrase) == "ADM. DESC. DE REC. DEL EDO"
    assert nz.normalize_organization(
        "Servicio de Administración Tributaria"
    ) == "S.A.T."
    assert nz.normalize_organization(
        "Secretaría de Administración Tributaria"
    ) == "S.A.T."


def test_field_abbreviations_and_email():
    assert nz.normalize_title("Licenciada") == "LIC."
    assert nz.normalize_title("señor") == "SEÑOR"
    assert nz.normalize_organization("Universidad Autónoma") == "UNI. AUT."
    assert nz.normalize_street("Avenida Sin Número") == "AV. SN."
    assert nz.normalize_street("S/N") == "SN"
    assert nz.normalize_email("  Ana@CORREO.MX ") == "ana@correo.mx"


def test_phone_removes_junk_words_only():
    assert nz.normalize_phone("Tel. 55-1234-5678") == "55 1234 5678"
    assert nz.normalize_phone("Notario Nombre") == "NOTARIO NOMBRE"
    assert nz.normalize_phone("") == ""


def test_rules_are_idempotent():
    samples = [
        nz.normalize_full_name,
        nz.normalize_organization,
        nz.normalize_job_role,
        nz.normalize_title,
        nz.normalize_phone,
        nz.normalize_street,
        nz.normalize_email,
    ]
    raw = "  Señora Universidad, Tel. 55 "
    for fn in samples:
        once = fn(raw)
        assert fn(once) == once


def test_normalize_shipment_fields_returns_only_normalized_keys():
    result = nz.normalize_shipment_fields({
        "name_receiver": "Juan",
        "street": "Central",
        "address_reference": "Puerta",
        "city": "no debe aparecer",
    })

    assert set(result) == {
        "name_receiver",
        "street",
        "num_street",
        "phone",
        "address_reference",
    }


def test_normalize_shipment_fields_uppercases_and_strips():
    result = nz.normalize_shipment_fields({
        "name_receiver": "  juan perez  ",
        "street": "  central  ",
        "address_reference": "  puerta gris  ",
    })

    assert result["name_receiver"] == "JUAN PEREZ"
    assert result["street"] == "CENTRAL"
    assert result["address_reference"] == "PUERTA GRIS"


def test_normalize_shipment_fields_handles_missing_values():
    result = nz.normalize_shipment_fields({})

    assert result["name_receiver"] == ""
    assert result["street"] == ""
    assert result["num_street"] == ""
    assert result["phone"] == ""
    assert result["address_reference"] == ""


@pytest.mark.parametrize(
    ("street", "expected"),
    [
        ("CALLE 12", "C. 12"),
        ("calle 12", "C. 12"),
        ("AVENIDA INSURGENTES", "AV. INSURGENTES"),
        ("BOULEVARD REFORMA", "BLVD. REFORMA"),
        ("CARRETERA FEDERAL", "CARR. FEDERAL"),
        ("EDIFICIO A", "EDIF. A"),
        ("CALLEJON 12", "CALLEJON 12"),
        ("Callejón 12", "CALLEJON 12"),
        ("CALLEJÓN, 12", "CALLEJON 12"),
        ("AVENIDAS NORTE", "AVENIDAS NORTE"),
    ],
)
def test_normalize_shipment_fields_abbreviates_whole_address_words(street, expected):
    result = nz.normalize_shipment_fields({"street": street})

    assert result["street"] == expected


def test_normalize_shipment_fields_abbreviates_address_reference():
    result = nz.normalize_shipment_fields({
        "address_reference": "Edificio B, calle 5",
    })

    assert result["address_reference"] == "EDIF. B C. 5"


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Doctor Juan Perez", "DR. JUAN PEREZ"),
        ("Doctora Ana Lopez", "DRA. ANA LOPEZ"),
        ("Maestro Juan", "MTRO. JUAN"),
        ("Maestra Ana", "MTRA. ANA"),
        ("Profesor Luis", "PROF. LUIS"),
        ("Profesora Ana", "PROFA. ANA"),
        ("Diputado Juan", "DIP. JUAN"),
        ("Diputada Ana", "DIP. ANA"),
        ("Senador Juan", "SEN. JUAN"),
        ("Senadora Ana", "SEN. ANA"),
        ("Presidente Juan", "PDTE. JUAN"),
        ("Presidenta Ana", "PDTA. ANA"),
        ("Administrador Juan", "ADMIN. JUAN"),
        ("Administradora Ana", "ADMIN. ANA"),
        ("Director General", "DIR. GRAL."),
        ("Gobernador Juan", "GOB. JUAN"),
        ("Titular Juan", "TIT. JUAN"),
        ("Secretario Juan", "SEC. JUAN"),
        ("Universidad Autonoma", "UNI AUT."),
        ("Órgano Interno de Control", "O.I.C."),
        ("Organo de Control Interno", "O.I.C."),
        ("Secretaria de Administracion Tributaria", "S.A.T."),
    ],
)
def test_normalize_shipment_fields_abbreviates_whole_title_words(name, expected):
    result = nz.normalize_shipment_fields({"name_receiver": name})

    assert result["name_receiver"] == expected


def test_normalize_shipment_fields_removes_special_characters():
    result = nz.normalize_shipment_fields({
        "name_receiver": 'Juan [Pérez], #1 "Oficial"',
        "street": "Reforma, [Norte] #12",
        "num_street": "No. 12-A",
        "phone": "Tel. 55-1234-5678",
        "address_reference": "Frente al edificio, (portería)",
    })

    assert result["name_receiver"] == "JUAN PEREZ 1 OFICIAL"
    assert result["street"] == "REFORMA NORTE 12"
    assert result["num_street"] == "12 A"
    assert result["phone"] == "55 1234 5678"
    assert result["address_reference"] == "FRENTE AL EDIF. PORTERIA"


def test_normalize_shipment_fields_keeps_abbreviation_periods():
    result = nz.normalize_shipment_fields({
        "name_receiver": "Dr. José Pérez",
        "street": "Av. Independencia, 10/2",
        "address_reference": "Frente al edificio.",
    })

    assert result["name_receiver"] == "DR. JOSE PEREZ"
    assert result["street"] == "AV. INDEPENDENCIA 102"
    assert result["address_reference"] == "FRENTE AL EDIF."


class _Page:
    items: list = []


def test_catalog_search_sends_normalized_query(monkeypatch):
    captured: dict[str, str] = {}

    def _capture(key):
        def fake(_token, search=None, **_kwargs):
            captured[key] = search
            return _Page()
        return fake

    monkeypatch.setattr(catalogs_service, "get_access_token", lambda: "tok")
    monkeypatch.setattr(catalogs_service.titles_api, "list_titles", _capture("title"))
    monkeypatch.setattr(catalogs_service.job_roles_api, "list_job_roles", _capture("role"))
    monkeypatch.setattr(
        catalogs_service.organizations_api,
        "list_organizations",
        _capture("org"),
    )

    catalogs_service.search_titles("doctor")
    catalogs_service.search_job_roles("director general")
    catalogs_service.search_organizations("servicio de administración tributaria")

    assert captured == {
        "title": "DR.",
        "role": "DIR. GRAL.",
        "org": "S.A.T.",
    }


def test_catalog_search_skips_api_when_normalized_query_is_too_short(monkeypatch):
    def fail(*_args, **_kwargs):
        raise AssertionError("no debe llamar a la API")

    monkeypatch.setattr(catalogs_service.titles_api, "list_titles", fail)
    assert catalogs_service.search_titles("ciudadano") == []


def test_title_abbreviation_accepts_two_characters():
    title = TitleInput(abbreviation="C.", meaning="Ciudadano")
    assert title.abbreviation == "C."


def test_job_role_abbreviation_accepts_enie():
    role = JobRoleInput(abbreviation="ÑIÑO", meaning="Niño")
    assert role.abbreviation == "ÑIÑO"
    with pytest.raises(ValidationError):
        JobRoleInput(abbreviation="DIR@", meaning="Director")


def test_job_role_fields_accept_digits():
    role = JobRoleInput(abbreviation="ADM 2", meaning="ADMINISTRADORA 2")
    assert role.abbreviation == "ADM 2"
    assert role.meaning == "ADMINISTRADORA 2"
