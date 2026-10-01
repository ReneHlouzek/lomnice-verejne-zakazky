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
