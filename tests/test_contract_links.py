import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_contract_links as link_builder
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


def test_same_source_conflicting_contract_numbers_are_not_addendum_candidates():
    base = {
        "id": "base", "title": "Služby v obecném hospodářském zájmu",
        "sources": [{"record": {"source": "registr-smluv", "source_id": "base",
            "title": "Smlouva o poskytnutí dotace na poskytování služeb v obecném hospodářském zájmu, č. OLP/4637/2016",
            "contract_number": "OLP/4637/2016", "supplier_ico": "70891508",
            "date": "2016-09-23"}}],
    }
    addendum = {
        "id": "add", "title": "Dodatek č. 1 ke smlouvě OLP/588/2016",
        "sources": [{"record": {"source": "registr-smluv", "source_id": "add",
            "title": "Dodatek č. 1 ke smlouvě o poskytnutí dotace na poskytování služeb v obecném hospodářském zájmu, č. OLP/588/2016",
            "contract_number": "OLP/588/2016", "supplier_ico": "70891508",
            "date": "2016-10-21"}}],
    }
    links, candidates = build_links([base, addendum])
    assert links == []
    assert candidates == []


def test_same_source_generic_project_overlap_is_not_review_candidate():
    base = {
        "id": "base", "title": "Oprava vodovodu Hrádka",
        "sources": [{"record": {"source": "registr-smluv", "source_id": "base",
            "title": "Veřejnoprávní smlouva o poskytnutí neinvestiční dotace - oprava vodovodu Hrádka",
            "supplier_ico": "49295934", "date": "2020-05-21"}}],
    }
    addendum = {
        "id": "add", "title": "Dodatek č. 1 - Košov - obnova vodovodu",
        "sources": [{"record": {"source": "registr-smluv", "source_id": "add",
            "title": "Dodatek č. 1 veřejnoprávní smlouvy - Košov - obnova vodovodu",
            "supplier_ico": "49295934", "date": "2025-09-22"}}],
    }
    links, candidates = build_links([base, addendum])
    assert links == []
    assert candidates == []


def test_explicit_related_addenda_are_linked():
    addendum_one = {
        "id": "add1", "title": "Dodatek č. 1",
        "sources": [{"record": {"source": "registr-smluv", "source_id": "845225",
            "title": "Dodatek č. 1 ke smlouvě", "contract_number": "06_D01_OLP_2674_2016",
            "related_contract_ids": ["2264882", "3753"]}}],
    }
    addendum_two = {
        "id": "add2", "title": "Dodatek č. 2",
        "sources": [{"record": {"source": "registr-smluv", "source_id": "2264882",
            "title": "Dodatek č. 2 ke smlouvě", "contract_number": "06-OLP/2674/2016",
            "related_contract_ids": ["845225"]}}],
    }
    links, candidates = build_links([addendum_one, addendum_two])
    assert len(links) == 1
    assert links[0]["reason"] == "explicit_related_contract_id"
    assert "related_contract_id=2264882" in links[0]["evidence"] or "related_contract_id=845225" in links[0]["evidence"]
    assert candidates == []


def test_primary_document_original_signing_date_confirms_addendum(monkeypatch):
    monkeypatch.setattr(link_builder, "DOCUMENT_PARENT_DATES", {"add": ["2024-12-11"]})
    base = {
        "id": "base", "title": "Košov - obnova vodovodu",
        "sources": [{"record": {
            "source": "registr-smluv", "source_id": "base",
            "title": "Veřejnoprávní smlouva o poskytnutí neinvestiční dotace - Košov, obnova vodovodu",
            "buyer_ico": "00275905", "supplier_ico": "49295934",
            "signed_date": "2024-12-11",
        }}],
    }
    addendum = {
        "id": "add", "title": "Dodatek č. 1 - Košov - obnova vodovodu",
        "sources": [{"record": {
            "source": "registr-smluv", "source_id": "add",
            "title": "Dodatek č. 1 veřejnoprávní smlouvy o poskytnutí neinvestiční dotace - Košov, obnova vodovodu",
            "buyer_ico": "00275905", "supplier_ico": "49295934",
            "signed_date": "2025-09-22",
        }}],
    }
    links, candidates = build_links([base, addendum])
    assert len(links) == 1
    assert links[0]["reason"] == "explicit_parent_contract_date_and_project"
    assert "document_original_contract_date=2024-12-11" in links[0]["evidence"]
    assert candidates == []


def test_document_date_without_shared_party_or_project_does_not_confirm(monkeypatch):
    monkeypatch.setattr(link_builder, "DOCUMENT_PARENT_DATES", {"add": ["2024-12-11"]})
    base = {
        "id": "base", "title": "Oprava vodovodu Hrádka",
        "sources": [{"record": {
            "source": "registr-smluv", "source_id": "base",
            "title": "Veřejnoprávní smlouva - oprava vodovodu Hrádka",
            "buyer_ico": "00275905", "supplier_ico": "11111111",
            "signed_date": "2024-12-11",
        }}],
    }
    addendum = {
        "id": "add", "title": "Dodatek č. 1 - Košov - obnova vodovodu",
        "sources": [{"record": {
            "source": "registr-smluv", "source_id": "add",
            "title": "Dodatek č. 1 veřejnoprávní smlouvy - Košov, obnova vodovodu",
            "buyer_ico": "00275905", "supplier_ico": "49295934",
            "signed_date": "2025-09-22",
        }}],
    }
    links, candidates = build_links([base, addendum])
    assert links == []
    assert candidates == []


def test_document_original_contract_date_is_extracted_from_text(tmp_path, monkeypatch):
    text_file = tmp_path / "addendum.txt"
    text_file.write_text(
        "Dodatek ke smlouvě o dotaci uzavřené dne 11. 12. 2024.\n"
        "Původní smlouva byla uzavřena dne 11. 12. 2024.",
        encoding="utf-8",
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        __import__("json").dumps({
            "records": [{
                "source_id": "add",
                "documents": [{"text_file": str(text_file)}],
            }]
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(link_builder, "DOC_MANIFEST", manifest)
    assert link_builder.document_referenced_contract_dates() == {
        "add": ["2024-12-11"]
    }


def test_shared_party_identity_normalizes_ico_digits():
    a = {"buyer_ico": "00275905", "supplier_ico": "49295934"}
    b = {"publisher_ico": "IČO: 00275905", "supplier_ico": None}
    assert link_builder.shared_party_identity(a, b)


def test_mismatched_attachment_text_is_ignored_for_contract_evidence(tmp_path, monkeypatch):
    text_file = tmp_path / "mismatched.txt"
    text_file.write_text(
        "Smlouva OLP/1234/2024 uzavřená dne 11. 12. 2024.",
        encoding="utf-8",
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        __import__("json").dumps({
            "records": [{
                "source_id": "add",
                "documents": [{
                    "text_file": "mismatched.txt",
                    "status": "content_mismatch_review",
                }],
            }]
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(link_builder, "ROOT", tmp_path)
    monkeypatch.setattr(link_builder, "DOC_MANIFEST", manifest)

    assert link_builder.document_referenced_contract_numbers() == {}
    assert link_builder.document_referenced_contract_dates() == {}




def test_document_project_title_can_confirm_addendum_parent(monkeypatch):
    monkeypatch.setattr(link_builder, "DOCUMENT_PARENT_DATES", {"37367969": ["2026-06-25"]})
    monkeypatch.setattr(
        link_builder,
        "DOCUMENT_PROJECT_TITLES",
        {"37367969": ["Lomnice nad Popelkou – Obnova vodovodu v Želechách"]},
    )
    base = {
        "id": "zelechy-base",
        "title": "Obnova vodovodu v Želechách",
        "sources": [{"record": {
            "source": "registr-smluv",
            "source_id": "36197262",
            "title": "Veřejnoprávní smlouva o poskytnutí investiční dotace - obnova vodovodu v Želechách",
            "signed_date": "2026-06-25",
            "buyer_ico": "00275905",
            "supplier_ico": "49295934",
        }}],
    }
    addendum = {
        "id": "zelechy-addendum",
        "title": "Dodatek č. 1 veřejnoprávní smlouvy o poskytnutí neinvestiční dotace",
        "sources": [{"record": {
            "source": "registr-smluv",
            "source_id": "37367969",
            "title": "Dodatek č. 1 veřejnoprávní smlouvy o poskytnutí neinvestiční dotace",
            "signed_date": "2026-09-30",
            "buyer_ico": "00275905",
            "supplier_ico": "49295934",
        }}],
    }

    links, candidates = build_links([base, addendum])
    assert len(links) == 1
    assert links[0]["source_id_a"] == "37367969" or links[0]["source_id_b"] == "37367969"
    assert links[0]["reason"] == "explicit_parent_contract_date_and_project"
    assert "document_original_contract_date=2026-06-25" in links[0]["evidence"]
    assert candidates == []



def test_document_project_title_extraction_handles_quoted_czech_project(tmp_path, monkeypatch):
    import json

    document_path = "data/documents/registr-smluv/37367969/001.txt"
    text_path = tmp_path / document_path
    text_path.parent.mkdir(parents=True)
    text_path.write_text(
        "Smluvní strany uzavírají dodatek na realizaci projektu "
        "„Lomnice nad Popelkou – Obnova vodovodu v Želechách“.",
        encoding="utf-8",
    )
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({
        "records": [{
            "source_id": "37367969",
            "documents": [{
                "status": "retained_existing_text",
                "text_file": document_path,
            }],
        }]
    }), encoding="utf-8")
    monkeypatch.setattr(link_builder, "DOC_MANIFEST", manifest_path)
    monkeypatch.setattr(link_builder, "ROOT", tmp_path)

    titles = link_builder.document_referenced_project_titles()
    assert titles["37367969"] == ["Lomnice nad Popelkou – Obnova vodovodu v Želechách"]



def test_document_project_title_extraction_supports_realization_of_action(tmp_path, monkeypatch):
    import json

    doc_root = tmp_path / "data" / "documents" / "registr-smluv"
    doc_root.mkdir(parents=True)
    text_file = doc_root / "3861664.txt"
    text_file.write_text(
        "Dodatek na  realizaci  akce: Lomnice nad Popelkou – obnova VH sítí "
        "na Karlovském náměstí“ o částku 602 000 Kč.",
        encoding="utf-8",
    )
    manifest = doc_root / "manifest.json"
    manifest.write_text(json.dumps({
        "records": [{
            "source_id": "3861664",
            "documents": [{
                "text_file": "data/documents/registr-smluv/3861664.txt",
                "status": "retained_existing_text",
            }],
        }]
    }), encoding="utf-8")
    monkeypatch.setattr(link_builder, "DOC_MANIFEST", manifest)
    monkeypatch.setattr(link_builder, "ROOT", tmp_path)

    titles = link_builder.document_referenced_project_titles()
    assert titles["3861664"]
    assert "Karlovském náměstí" in titles["3861664"][0]


def test_generic_document_parent_is_not_linked_when_date_and_party_are_ambiguous(monkeypatch):
    monkeypatch.setattr(link_builder, "DOCUMENT_PARENT_DATES", {"3861664": ["2017-03-23"]})
    monkeypatch.setattr(
        link_builder,
        "DOCUMENT_PROJECT_TITLES",
        {"3861664": ["Lomnice nad Popelkou – obnova VH sítí na Karlovském náměstí"]},
    )
    addendum = {
        "id": "karlovske-addendum",
        "title": "Dodatek č. 1 k veřejnoprávní smlouvě o poskytnutí neinvestiční dotace",
        "sources": [{"record": {
            "source": "registr-smluv", "source_id": "3861664",
            "title": "Dodatek č. 1 k veřejnoprávní smlouvě o poskytnutí neinvestiční dotace",
            "signed_date": "2017-12-12", "buyer_ico": "00275905", "supplier_ico": "49295934",
        }}],
    }
    bases = []
    for source_id in ("1426690", "1426691"):
        bases.append({
            "id": f"base-{source_id}",
            "title": "Veřejnoprávní smlouva o poskytnutí neinvestiční dotace z rozpočtu města Lomnice nad Popelkou",
            "sources": [{"record": {
                "source": "registr-smluv", "source_id": source_id,
                "title": "Veřejnoprávní smlouva o poskytnutí neinvestiční dotace z rozpočtu města Lomnice nad Popelkou",
                "signed_date": "2017-03-23", "buyer_ico": "00275905", "supplier_ico": "49295934",
            }}],
        })
    links, candidates = build_links(bases + [addendum])
    assert links == []
    assert candidates == []


def test_karlovske_namesti_addendum_links_by_date_project_and_party(monkeypatch):
    monkeypatch.setattr(link_builder, "DOCUMENT_PARENT_DATES", {"3861664": ["2017-03-23"]})
    monkeypatch.setattr(
        link_builder,
        "DOCUMENT_PROJECT_TITLES",
        {"3861664": ["Lomnice nad Popelkou – obnova VH sítí na Karlovském náměstí"]},
    )
    base = {
        "id": "karlovske-base",
        "title": "Veřejnoprávní smlouva o poskytnutí neinvestiční dotace z rozpočtu města Lomnice nad Popelkou",
        "sources": [{"record": {
            "source": "registr-smluv",
            "source_id": "1426690",
            "title": "Veřejnoprávní smlouva o poskytnutí neinvestiční dotace z rozpočtu města Lomnice nad Popelkou",
            "signed_date": "2017-03-23",
            "buyer_ico": "00275905",
            "supplier_ico": "49295934",
        }}],
    }
    addendum = {
        "id": "karlovske-addendum",
        "title": "Dodatek č. 1 k veřejnoprávní smlouvě o poskytnutí neinvestiční dotace",
        "sources": [{"record": {
            "source": "registr-smluv",
            "source_id": "3861664",
            "title": "Dodatek č. 1 k veřejnoprávní smlouvě o poskynutí neinvestiční dotace",
            "signed_date": "2017-12-12",
            "buyer_ico": "00275905",
            "supplier_ico": "49295934",
        }}],
    }

    links, candidates = build_links([base, addendum])
    assert len(links) == 1
    assert links[0]["reason"] == "explicit_parent_contract_date_party_unique_base"
    assert "document_original_contract_date=2017-03-23" in links[0]["evidence"]
    assert "generic_base_title_unique_date_and_party_match=true" in links[0]["evidence"]
    assert candidates == []


def test_jilemnicka_addenda_conflicting_parent_date_never_confirm_link(monkeypatch):
    # The two Jilemnická addenda say their base agreement was signed on
    # 2023-09-22, while the only currently found base record is dated 2022-09-22.
    # A shared project title and party IDs must not override that date conflict.
    monkeypatch.setattr(link_builder, "DOCUMENT_PARENT_DATES", {
        "25099803": ["2023-09-22"],
        "28586216": ["2023-09-22"],
    })
    monkeypatch.setattr(link_builder, "DOCUMENT_PROJECT_TITLES", {
        "25099803": ["Lomnice nad Popelkou – Obnova vodovodu a kanalizace Jilemnická ulice"],
        "28586216": ["Lomnice nad Popelkou – Obnova vodovodu a kanalizace Jilemnická ulice"],
    })
    base = {
        "id": "jilemnicka-base",
        "title": "Obnova vodovodu a kanalizace Jilemnická ulice",
        "sources": [{"record": {
            "source": "registr-smluv", "source_id": "unverified-base",
            "title": "Veřejnoprávní smlouva o poskytnutí investiční dotace z rozpočtu města Lomnice nad Popelkou",
            "signed_date": "2022-09-22",
            "buyer_ico": "00275905", "supplier_ico": "49295934",
        }}],
    }
    addendum = {
        "id": "jilemnicka-addendum-1",
        "title": "Dodatek č. 1 – Obnova vodovodu a kanalizace Jilemnická ulice",
        "sources": [{"record": {
            "source": "registr-smluv", "source_id": "unverified-addendum",
            "title": "Dodatek č. 1 veřejnoprávní smlouvy o poskytnutí investiční dotace – Jilemnická ulice",
            "signed_date": "2023-12-01",
            "buyer_ico": "00275905", "supplier_ico": "49295934",
        }}],
    }

    links, _candidates = build_links([base, addendum])
    assert links == []


def test_jilemnicka_links_are_supported_by_official_council_resolutions():
    base = {
        "id": "jilemnicka-base",
        "title": "Jilemnická – obnova vodovodu a kanalizace",
        "sources": [{"record": {
            "source": "registr-smluv", "source_id": "20244341",
            "title": "Veřejnoprávní smlouva o poskytnutí investiční dotace z rozpočtu města Lomnice nad Popelkou",
            "signed_date": "2022-09-22",
            "buyer_ico": "00275905", "supplier_ico": "49295934",
        }}],
    }
    addendum_one = {
        "id": "jilemnicka-addendum-one",
        "title": "Dodatek č. 1 – Jilemnická",
        "sources": [{"record": {
            "source": "registr-smluv", "source_id": "25099803",
            "title": "Dodatek č. 1 veřejnoprávní smlouvy o poskytnutí investiční dotace",
            "signed_date": "2023-12-12",
            "buyer_ico": "00275905", "supplier_ico": "49295934",
        }}],
    }
    addendum_two = {
        "id": "jilemnicka-addendum-two",
        "title": "Dodatek č. 2 – Jilemnická",
        "sources": [{"record": {
            "source": "registr-smluv", "source_id": "28586216",
            "title": "Dodatek č. 2 veřejnoprávní smlouvy o poskytnutí investiční dotace",
            "signed_date": "2024-10-14",
            "buyer_ico": "00275905", "supplier_ico": "49295934",
        }}],
    }

    links, candidates = build_links([base, addendum_one, addendum_two])
    by_addendum = {str(row["source_id_a"]): row for row in links}
    by_addendum.update({str(row["source_id_b"]): row for row in links})
    assert len(links) == 2
    for addendum_id, resolution in (("25099803", "71/23/Z"), ("28586216", "55/24/Z")):
        row = next(
            row for row in links
            if addendum_id in (str(row["source_id_a"]), str(row["source_id_b"]))
        )
        assert row["reason"] == "explicit_parent_official_council_resolution"
        assert f"official_council_resolution={resolution}" in row["evidence"]
        assert any(item.startswith("official_council_resolution_url=https://") for item in row["evidence"])
    assert candidates == []

