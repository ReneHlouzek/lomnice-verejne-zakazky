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


def test_group_score_checks_all_members():
    group = [
        {"title": "Starý obecný název", "supplier_ico": "12345678"},
        {"title": "Modernizace učeben ZUS stavební práce", "supplier_ico": "12345678"},
    ]
    new = {"title": "Modernizace učeben ZUS stavební práce dodatek", "supplier_ico": "12345678"}
    score, reason, _ = resolver.group_score(new, group)
    assert score >= 0.72
    assert reason == "addendum_core_title"


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
