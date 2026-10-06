import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_contract_links import build_links


def test_explicit_addendum_reference_is_contractual_not_fuzzy():
    base = {
        "id": "base", "title": "Původní smlouva",
        "sources": [{"record": {"source": "registr-smluv", "source_id": "1",
            "title": "Smlouva o dílo - oprava", "contract_number": "07-OLP2373/2021"}}],
    }
    addendum = {
        "id": "add", "title": "Dodatek",
        "sources": [{"record": {"source": "registr-smluv", "source_id": "2",
            "title": "Dodatek č. 3 ke smlouvě 07-OLP2373/2021", "contract_number": "D-3"}}],
    }
    links, candidates = build_links([base, addendum])
    assert len(links) == 1
    assert links[0]["kind"] == "contractual"
    assert links[0]["confidence"] == "explicit"
    assert links[0]["reason"] == "explicit_parent_contract_number"
    assert candidates == []


def test_similar_titles_alone_do_not_create_a_link():
    a = {"id": "a", "title": "Oprava komunikace", "sources": [{"record": {"title": "Oprava komunikace"}}]}
    b = {"id": "b", "title": "Oprava komunikace", "sources": [{"record": {"title": "Oprava komunikace"}}]}
    links, candidates = build_links([a, b])
    assert links == []
    assert candidates == []


def test_fuzzy_match_is_candidate_not_confirmed_link():
    a = {"id": "a", "title": "Oprava budovy", "sources": [{"record": {
        "source": "registr-smluv", "source_id": "1", "title": "Oprava budovy",
        "supplier_ico": "12345678", "price": 100000}}]}
    b = {"id": "b", "title": "Oprava budovy", "sources": [{"record": {
        "source": "vhodne-uverejneni", "source_id": "2", "title": "Oprava budovy",
        "supplier_ico": "12345678", "price": 100000}}]}
    links, candidates = build_links([a, b])
    assert links == []
    assert candidates


def test_related_contract_number_is_explicit():
    base = {
        "id": "base", "title": "Původní smlouva",
        "sources": [{"record": {"source": "registr-smluv", "source_id": "100",
            "title": "Smlouva", "contract_number": "07-OLP/2373/2021"}}],
    }
    addendum = {
        "id": "add", "title": "Dodatek",
        "sources": [{"record": {"source": "registr-smluv", "source_id": "101",
            "title": "Dodatek č. 2 ke smlouvě", "contract_number": "07-OLP/2373/2022",
            "related_contract_numbers": ["07-OLP/2373/2021"]}}],
    }
    links, candidates = build_links([base, addendum])
    assert len(links) == 1
    assert links[0]["reason"] == "explicit_parent_contract_number"
    assert links[0]["evidence"] == ["07-OLP/2373/2021"]
    assert candidates == []


def test_versioned_contract_family_is_explicit_link():
    base = {
        "id": "base", "title": "Nájem NP",
        "sources": [{"record": {"source": "registr-smluv", "source_id": "774449",
            "title": "Lomnice nad Popelkou - nájem NP pro OOP",
            "contract_number": "924004797.00.000 / KRPL-68860-8/ČJ-2016-1800SU-5"}}],
    }
    addendum = {
        "id": "add", "title": "Dodatek 1",
        "sources": [{"record": {"source": "registr-smluv", "source_id": "2316654",
            "title": "Dodatek 1 Lomnice n.Popelkou - nájem NP",
            "contract_number": "924004797.00.001 / KRPL-68860-12/ČJ-2016-1800SU-5"}}],
    }
    links, candidates = build_links([base, addendum])
    assert len(links) == 1
    assert links[0]["reason"] == "explicit_parent_contract_number"
    assert links[0]["evidence"] == [
        "924004797.00.000 / KRPL-68860-8/ČJ-2016-1800SU-5",
        "924004797.00.001 / KRPL-68860-12/ČJ-2016-1800SU-5",
    ]
    assert candidates == []


def test_same_source_distinctive_addendum_is_review_candidate():
    base = {
        "id": "base", "title": "Košov - obnova vodovodu",
        "sources": [{"record": {"source": "registr-smluv", "source_id": "base",
            "title": "Veřejnoprávní smlouva o poskytnutí investiční dotace - Košov - obnova vodovodu",
            "supplier_ico": "49295934", "price": 2880000, "date": "2024-12-11"}}],
    }
    addendum = {
        "id": "add", "title": "Dodatek č. 1 - Košov - obnova vodovodu",
        "sources": [{"record": {"source": "registr-smluv", "source_id": "add",
            "title": "Dodatek č. 1 veřejnoprávní smlouvy o poskytnutí neinvestiční dotace - Košov - obnova vodovodu",
            "supplier_ico": "49295934", "price": 1323950.25, "date": "2025-09-22"}}],
    }
    links, candidates = build_links([base, addendum])
    assert links == []
    assert len(candidates) == 1
    assert candidates[0]["reason"] == "candidate_addendum_core_title"
    assert candidates[0]["confidence"] == "review"


def test_exact_contract_number_family_matches():
    base = {
        "id": "base", "title": "Karavanové stání",
        "sources": [{"record": {"source": "registr-smluv", "source_id": "base",
            "title": "Poskytnutí účelové dotace - Karavanové stání",
            "contract_number": "07-OLP/2373/2021"}}],
    }
    addendum = {
        "id": "add", "title": "Dodatek č. 2 ke smlouvě - Karavanové stání",
        "sources": [{"record": {"source": "registr-smluv", "source_id": "add",
            "title": "Dodatek č. 2 ke smlouvě o poskytnutí účelové dotace - Karavanové stání",
            "contract_number": "07-OLP/2373/2021"}}],
    }
    links, candidates = build_links([base, addendum])
    assert len(links) == 1
    assert links[0]["reason"] == "explicit_parent_contract_number"
    assert candidates == []


def test_compact_contract_number_family_matches_slash_version():
    base = {
        "id": "base", "title": "Karavanové stání",
        "sources": [{"record": {"source": "registr-smluv", "source_id": "base",
            "title": "Poskytnutí účelové dotace - Karavanové stání",
            "contract_number": "07-OLP/2373/2021"}}],
    }
    addendum = {
        "id": "add", "title": "Dodatek č. 3 ke smlouvě - Karavanové stání",
        "sources": [{"record": {"source": "registr-smluv", "source_id": "add",
            "title": "Dodatek č. 3 ke smlouvě o poskytnutí účelové dotace - Karavanové stání",
            "contract_number": "07-OLP2373/2021"}}],
    }
    links, candidates = build_links([base, addendum])
    assert len(links) == 1
    assert links[0]["reason"] == "explicit_parent_contract_number"
    assert candidates == []


def test_liberecky_kraj_addendum_exact_number_is_explicit():
    base = {
        "id": "base", "title": "Účelová dotace Libereckému kraji",
        "sources": [{"record": {"source": "registr-smluv", "source_id": "base",
            "title": "Smlouva o poskytnutí účelové dotace Libereckému kraji",
            "contract_number": "06-OLP/2674/2016"}}],
    }
    addendum = {
        "id": "add", "title": "Dodatek č. 2 ke smlouvě - havárie zdi",
        "sources": [{"record": {"source": "registr-smluv", "source_id": "add",
            "title": "Dodatek č. 2 ke smlouvě o poskytnutí účelové dotace Libereckému kraji",
            "contract_number": "06-OLP/2674/2016"}}],
    }
    links, candidates = build_links([base, addendum])
    assert len(links) == 1
    assert links[0]["reason"] == "explicit_parent_contract_number"
    assert candidates == []
