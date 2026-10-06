import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import resolve_projects as resolver
import analyze_projects as analyzer


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
