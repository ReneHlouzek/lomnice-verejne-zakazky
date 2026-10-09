import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import resolve_projects as resolver
import analyze_projects as analyzer
import import_registr_smluv as registr
import extract_registr_documents as doc_extractor


def test_czech_price_parsing():
    assert resolver.price("2 015 798,00 Kč") == 2015798.0
    assert resolver.price("2.015.798,00 Kč") == 2015798.0
    assert analyzer.num("6 072 914,50 Kč") == 6072914.5


def test_date_parsing():
    assert resolver.date_value("16.09.2026") == "2026-09-16"
    assert analyzer.date_value("2026-09-16T12:30:00").isoformat() == "2026-09-16"


def test_exact_identifier_is_strongest_match():
    a = {"contract_id": "ABC-123", "title": "Jiný název"}
    b = {"contract_id": "ABC-123", "title": "Úplně jiný název"}
    score, reason, evidence = resolver.score(a, b)
    assert score == 1.0
    assert reason == "exact_identifier"
    assert evidence == ["ABC-123"]




def test_addendum_links_to_base_by_related_contract_id():
    base = {
        "source": "registr-smluv",
        "source_id": "15970715",
        "title": "Poskytnutí účelové dotace z rozpočtu Libereckého kraje na projekt Karavanové stání",
        "contract_number": "07-OLP/2373/2021",
    }
    addendum = {
        "source": "registr-smluv",
        "source_id": "20176309",
        "title": "Dodatek č. 1 ke smlouvě o poskytnutí účelové dotace na projekt karavanová stání",
        "contract_number": "07-OLP/2373/2022",
        "related_contract_ids": ["15970715"],
    }
    score, reason, evidence = resolver.score(addendum, base)
    assert score == 1.0
    assert reason == "explicit_related_contract_id"
    assert evidence == ["related_contract_id=15970715"]


def test_spaced_versioned_contract_family_is_normalized():
    assert resolver.contract_family_matches(
        "924004797.00.001 / KRPL-68860-12/ČJ-2016-1800SU-5",
        "924004797.00.000 / KRPL-68860-8/ČJ-2016-1800SU-5",
    )


def test_versioned_contract_numbers_share_a_family():
    assert resolver.contract_family_matches(
        "924004797.00.001 / KRPL-68860-12/ČJ-2016-1800SU-5",
        "924004797.00.000 / KRPL-68860-8/ČJ-2016-1800SU-5",
    )
    assert resolver.contract_family_matches(
        "924004797.00.002 / KRPL-68860-32/ČJ-2016-1800SU",
        "924004797.00.000 / KRPL-68860-8/ČJ-2016-1800SU-5",
    )


def test_addendum_links_to_base_by_explicit_contract_number():
    base = {
        "source": "registr-smluv",
        "title": "Smlouva o dílo - oprava komunikace",
        "contract_number": "07-OLP2373/2021",
        "supplier_ico": "12345678",
    }
    addendum = {
        "source": "registr-smluv",
        "title": "Dodatek č. 3 ke smlouvě 07-OLP2373/2021",
        "contract_number": "D-2024-03",
        "supplier_ico": "87654321",
    }
    score, reason, evidence = resolver.score(addendum, base)
    assert score == 1.0
    assert reason == "explicit_parent_contract_number"
    assert evidence == ["07-OLP2373/2021"]


def test_group_score_checks_all_members():
    group = [
        {"title": "Starý obecný název", "supplier_ico": "12345678"},
        {"title": "Modernizace učeben ZUS stavební práce", "supplier_ico": "12345678"},
    ]
    new = {"title": "Modernizace učeben ZUS stavební práce dodatek", "supplier_ico": "12345678"}
    score, reason, _ = resolver.group_score(new, group)
    assert score >= 0.72
    assert reason == "candidate_addendum_core_title"


def test_procurement_signal_does_not_overclaim():
    explicit = {"title": "Smlouva o dílo - veřejná zakázka Revitalizace rybníka"}
    likely = {"title": "Smlouva o dílo - Oprava místní komunikace"}
    plain = {"title": "Darovací smlouva"}
    assert resolver.procurement_signal(explicit)["level"] == "explicit"
    assert resolver.procurement_signal(likely)["level"] == "likely"
    assert resolver.procurement_signal(plain)["level"] == "none"


def test_generic_addendum_titles_are_not_strong_candidates():
    base = {
        "title": "Veřejnoprávní smlouva o poskytnutí investiční dotace z rozpočtu města Lomnice nad Popelkou",
        "supplier_ico": "49295934",
        "date": "2024-01-10",
    }
    addendum = {
        "title": "Dodatek č. 1 k veřejnoprávní smlouvě o poskytnutí investiční dotace z rozpočtu města Lomnice nad Popelkou",
        "supplier_ico": "49295934",
        "date": "2024-01-10",
    }
    score, reason, _ = resolver.score(addendum, base)
    assert score < 0.82


def test_generic_same_supplier_contracts_are_not_auto_merged():
    a = {"title": "Veřejnoprávní smlouva o poskytnutí neinvestiční dotace z rozpočtu města", "supplier_ico": "49295934", "price": 500000}
    b = {"title": "Veřejnoprávní smlouva o poskytnutí neinvestiční dotace z rozpočtu města - obnova vodovodu", "supplier_ico": "49295934", "price": 2880000}
    score, reason, _ = resolver.score(a, b)
    assert score < 0.82


def test_lifecycle_classification():
    assert resolver.classify({"title": "Dodatek č. 2 ke smlouvě"}) == "addendum"
    assert resolver.classify({"title": "Smlouva o dílo"}) == "contract"
    assert resolver.classify({"title": "Výsledek zadávacího řízení"}) == "award"
    assert resolver.classify({"title": "Veřejná zakázka"}) == "tender"


def test_price_change_uses_contract_baseline_and_latest_observation():
    project = {
        "id": "p-test",
        "sources": [
            {"record": {"source": "test", "source_id": "1", "title": "Smlouva o dílo", "date": "2026-01-01", "price": "100000"}},
            {"record": {"source": "test", "source_id": "2", "title": "Dodatek č. 1", "date": "2026-02-01", "price": "110000"}},
            {"record": {"source": "test", "source_id": "3", "title": "Dodatek č. 2", "date": "2026-03-01", "price": "125000"}},
        ],
    }
    result = analyzer.analyze(project)
    assert result["financial"]["baseline_price"] == 100000.0
    assert result["financial"]["current_observed_price"] == 125000.0
    assert result["financial"]["absolute_change"] == 25000.0
    assert result["financial"]["percent_change"] == 25.0
    assert result["financial"]["addendum_count"] == 2


def test_analysis_is_neutral_and_provenance_preserving():
    project = {"id": "p-test", "sources": [{"record": {"source": "official", "source_id": "X", "title": "Smlouva", "date": "2026-01-01", "price": 100}}]}
    result = analyzer.analyze(project)
    assert result["timeline"][0]["source_id"] == "X"
    assert "wrongdoing" in result["methodology"]


def test_same_source_tender_and_resulting_contract_can_be_linked():
    tender = {
        "source": "vhodne-uverejneni",
        "title": "Modernizace učeben ZUŠ - stavební práce",
        "type": "tender",
        "supplier_ico": "25937499",
        "date": "2025-01-28",
        "contract_signed_date": "2025-04-01",
        "price": 15485071.64,
    }
    contract = {
        "source": "vhodne-uverejneni",
        "title": "Modernizace učeben ZUŠ - stavební práce",
        "type": "contract",
        "supplier_ico": "25937499",
        "date": "2025-04-01",
        "price": 15485071.64,
    }
    score, reason, _ = resolver.group_score(contract, [tender])
    assert score >= 0.82
    assert reason == "supplier_title_price"


def test_contract_family_matches_common_addendum_formats():
    assert resolver.contract_family_matches(
        "924004797.00.001 / KRPL-68860-12/ČJ-2016-1800SU-5",
        "924004797.00.000 / KRPL-68860-8/ČJ-2016-1800SU-5",
    )
    assert resolver.contract_family_matches(
        "06_D01_OLP_2674_2016",
        "06-OLP/2674/2016",
    )
    assert resolver.contract_family_matches(
        "OLP/3394/2023/1",
        "OLP/3394/2023",
    )


def test_addendum_without_independent_evidence_is_not_strong():
    base = {
        "title": "Smlouva o poskytnutí dotace",
        "supplier_ico": "49295934",
        "date": "2024-01-01",
    }
    addendum = {
        "title": "Dodatek č. 1 ke smlouvě o poskytnutí dotace",
        "supplier_ico": "49295934",
        "date": "2025-12-31",
    }
    score, _, _ = resolver.score(addendum, base)
    assert score < 0.82


def test_registry_detail_relationship_extraction_handles_public_page_markup():
    html = """
    <div>ID návazné smlouvy:</div>
    <a href="/smlouva/15970715">15970715</a>
    """
    assert registr.extract_related_contract_ids_from_html(html) == ["15970715"]


def test_registry_detail_attachment_extraction_includes_doc_and_skips_metadata_pdf():
    page_html = """
    <a href="/smlouva/soubor/42395429/Dodatek%20%C4%8D.%201.doc">Dodatek</a>
    <a href="/smlouva/34905225/pdf/registr_smluv_smlouva_34905225.pdf">Metadata</a>
    <a href="/smlouva/soubor/999/registr_smluv_smlouva_34905225.pdf">Metadata file</a>
    """
    assert registr.extract_attachment_links_from_html(page_html) == [
        {
            "url": "https://smlouvy.gov.cz/smlouva/soubor/42395429/Dodatek%20%C4%8D.%201.doc",
            "name": "Dodatek%20%C4%8D.%201.doc",
        }
    ]


def test_registry_import_preserves_known_attachments_for_same_version_only():
    attachment = {
        "url": "https://smlouvy.gov.cz/smlouva/soubor/1234/contract.doc",
        "name": "contract.doc",
    }
    old = {"version_id": "34905225", "attachments": [attachment]}
    same_version = {"version_id": "34905225", "attachments": []}
    newer_version = {"version_id": "34905226", "attachments": []}

    assert registr.preserve_attachments_for_same_version(same_version, old)["attachments"] == [attachment]
    assert "attachments" not in registr.preserve_attachments_for_same_version(newer_version, old)



def test_attachment_filename_mismatch_is_flagged_for_review():
    filename = "%C5%BDelechy%20-%20Dodatek%20%C4%8D.%201.docx"
    unrelated_text = "Smlouva o služebnosti uzavřená mezi městem Hodonín a společností T-Mobile."
    matching_text = "Dodatek č. 1 k dotaci na akci Želechy."
    assert doc_extractor.filename_content_mismatch(filename, unrelated_text)
    assert not doc_extractor.filename_content_mismatch(filename, matching_text)


def test_legacy_doc_extraction_falls_back_to_libreoffice_when_antiword_is_missing(tmp_path):
    from unittest.mock import patch

    target = tmp_path / "input.doc"
    target.write_bytes(b"legacy doc fixture")

    def fake_run(command, **kwargs):
        if command[0] == "antiword":
            raise FileNotFoundError("antiword")
        assert command[0] == "libreoffice"
        target.with_suffix(".txt").write_text("Extracted legacy Word text", encoding="utf-8")
        return type("Result", (), {"stdout": "", "stderr": ""})()

    with patch("extract_registr_documents.subprocess.run", side_effect=fake_run):
        assert doc_extractor.extract_legacy_doc(target, str(tmp_path)) == "Extracted legacy Word text"


def test_registry_import_includes_city_as_counterparty_when_other_body_publishes():
    city_ico = "00275905"
    publisher_icos = {"12345678"}
    all_icos = {"12345678", city_ico}
    assert registr.record_involves_ico(publisher_icos, all_icos, city_ico)


def test_registry_import_excludes_records_unrelated_to_city():
    city_ico = "00275905"
    publisher_icos = {"12345678"}
    all_icos = {"12345678", "87654321"}
    assert not registr.record_involves_ico(publisher_icos, all_icos, city_ico)


def test_registry_import_reprocesses_history_when_filter_scope_changes():
    old_manifest = {
        "processed_dumps": {"https://data.smlouvy.gov.cz/dump_2024_01.xml": ""}
    }
    assert registr.processed_dumps_for_current_filter(old_manifest) == {}


def test_registry_import_keeps_history_markers_for_current_filter():
    processed = {"https://data.smlouvy.gov.cz/dump_2024_01.xml": ""}
    current_manifest = {
        "filter_version": registr.FILTER_VERSION,
        "processed_dumps": processed,
    }
    assert registr.processed_dumps_for_current_filter(current_manifest) == processed
