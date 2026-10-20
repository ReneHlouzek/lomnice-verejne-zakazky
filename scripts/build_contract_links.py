"""Build an explainable register of contractual links and review candidates."""
from __future__ import annotations
import json
import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import resolve_projects as resolver


def unique_evidence(values):
    seen = set()
    result = []
    for value in values:
        text = str(value or "").strip()
        key = resolver.norm(text)
        if not text or key in seen:
            continue
        seen.add(key)
        result.append(text)
    return result


DOC_MANIFEST = ROOT / "data" / "documents" / "registr-smluv" / "manifest.json"

def document_referenced_contract_numbers():
    if not DOC_MANIFEST.exists():
        return {}
    try:
        manifest = json.loads(DOC_MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    out = {}
    for row in manifest.get("records", []):
        sid = str(row.get("source_id") or "").strip()
        if not sid:
            continue
        refs = []
        for doc in row.get("documents", []):
            # A known filename/content mismatch is not reliable evidence for
            # contractual links, even when an extracted text file exists.
            if doc.get("status") == "content_mismatch_review":
                continue
            path = doc.get("text_file")
            if not path:
                continue
            file_path = ROOT / path
            try:
                text = file_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            refs.extend(re.findall(r"\b(?:[A-Z]{1,8}[-_/]?)?\d{1,8}[-_/][A-Z0-9ČŠŽĚŘŤŤÚŮÁÉÍÓÝa-zčšžěřťúůáéíóý]{1,12}[-_/]\d{2,4}\b", text, flags=re.IGNORECASE))
            refs.extend(re.findall(r"\b(?:OLP|KRPL|ČJ|CJ)[-_/ ]?\d{2,8}[-_/]\d{4}\b", text, flags=re.IGNORECASE))
        if refs:
            out[sid] = unique_evidence(refs)
    return out


DOCUMENT_REFS = document_referenced_contract_numbers()


def document_referenced_contract_dates():
    """Return dates explicitly attached to a referenced original agreement in document text."""
    if not DOC_MANIFEST.exists():
        return {}
    try:
        manifest = json.loads(DOC_MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    out = {}
    pattern = re.compile(
        r"\b(?:smlouvy|smlouva|smlouvě|smlouvou)\b.{0,260}?\b(?:uzavřen[áéou]*|ze dne)\s*(?:dne\s*)?"
        r"(\d{1,2}\.\s*\d{1,2}\.\s*\d{4})",
        flags=re.IGNORECASE | re.DOTALL,
    )
    for row in manifest.get("records", []):
        sid = str(row.get("source_id") or "").strip()
        if not sid:
            continue
        dates = []
        for doc in row.get("documents", []):
            # Never infer parent contract identifiers/dates from a flagged
            # attachment whose content does not match its declared filename.
            if doc.get("status") == "content_mismatch_review":
                continue
            path = doc.get("text_file")
            if not path:
                continue
            try:
                body = (ROOT / path).read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for match in pattern.finditer(body):
                raw = re.sub(r"\s+", "", match.group(1))
                try:
                    from datetime import datetime
                    dates.append(datetime.strptime(raw, "%d.%m.%Y").date().isoformat())
                except ValueError:
                    continue
        if dates:
            out[sid] = sorted(set(dates))
    return out


DOCUMENT_PARENT_DATES = document_referenced_contract_dates()


def document_referenced_project_titles():
    """Extract project names explicitly quoted in addendum text."""
    if not DOC_MANIFEST.exists():
        return {}
    try:
        manifest = json.loads(DOC_MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    pattern = re.compile(
        r"na\s+realizaci\s+(?:projektu|akce)\s*:?\s*[„“\"\']{0,2}\s*(.{8,220}?)(?:[”„“\"\']{1,2})",
        flags=re.IGNORECASE | re.DOTALL,
    )
    out = {}
    for row in manifest.get("records", []):
        sid = str(row.get("source_id") or "").strip()
        if not sid:
            continue
        titles = []
        for doc in row.get("documents", []):
            if doc.get("status") == "content_mismatch_review":
                continue
            path = doc.get("text_file")
            if not path:
                continue
            try:
                body = (ROOT / path).read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for match in pattern.finditer(body):
                title = re.sub(r"\s+", " ", match.group(1)).strip(" .,:;")
                if len(title) >= 8:
                    titles.append(title)
        if titles:
            out[sid] = unique_evidence(titles)
    return out


DOCUMENT_PROJECT_TITLES = document_referenced_project_titles()


def shared_party_identity(a, b):
    """Require at least one shared, non-empty official party identifier."""
    keys = ("buyer_ico", "supplier_ico", "publisher_ico")
    left = {re.sub(r"\D", "", str(a.get(key) or "")) for key in keys}
    right = {re.sub(r"\D", "", str(b.get(key) or "")) for key in keys}
    left = {value for value in left if len(value) == 8}
    right = {value for value in right if len(value) == 8}
    return bool(left & right)


def generic_base_title(record):
    """Identify the one known generic municipal grant-contract title form."""
    return resolver.norm(record.get("title")) == resolver.norm(
        "Veřejnoprávní smlouva o poskytnutí neinvestiční dotace "
        "z rozpočtu města Lomnice nad Popelkou"
    )


def unique_document_parent_bases(projects):
    """Find unique bases supported by an attachment's date and official party IDs."""
    candidates = {}
    for project in projects:
        for source in project.get("sources", []):
            addendum = source.get("record", {})
            if not resolver.is_addendum(addendum):
                continue
            add_id = str(addendum.get("source_id") or "").strip()
            dates = set(DOCUMENT_PARENT_DATES.get(add_id, []))
            if not add_id or not dates:
                continue
            for other_project in projects:
                for other_source in other_project.get("sources", []):
                    base = other_source.get("record", {})
                    if resolver.is_addendum(base) or not shared_party_identity(addendum, base):
                        continue
                    base_date = resolver.date_value(
                        base.get("signed_date") or base.get("date") or base.get("published")
                    )
                    base_id = str(base.get("source_id") or base.get("version_id") or "").strip()
                    if base_id and base_date in dates:
                        candidates.setdefault(add_id, set()).add(base_id)
    return candidates


# Manually verified links supported by official council resolutions. Keep this
# allowlist narrow and attach the resolution identifier and official source URL
# to the generated evidence so each exception remains auditable.
OFFICIAL_RESOLUTION_PARENT_LINKS = {
    frozenset(("20244341", "25099803")): {
        "resolution": "71/23/Z",
        "resolution_date": "2023-12-06",
        "url": "https://lomnicenadpopelkou.cz/assets/File.ashx?id_dokumenty=21831&id_org=8675",
    },
    frozenset(("20244341", "28586216")): {
        "resolution": "55/24/Z",
        "resolution_date": "2024-09-25",
        "url": "https://www.lomnicenadpopelkou.cz/assets/File.ashx?id_dokumenty=23045&id_org=8675",
    },
}


def official_resolution_parent_evidence(addendum, base):
    """Return auditable evidence when an official council resolution names the parent chain."""
    if not resolver.is_addendum(addendum) or resolver.is_addendum(base):
        return []
    add_id = str(addendum.get("source_id") or addendum.get("version_id") or "").strip()
    base_id = str(base.get("source_id") or base.get("version_id") or "").strip()
    resolution = OFFICIAL_RESOLUTION_PARENT_LINKS.get(frozenset((add_id, base_id)))
    if not resolution or add_id == base_id:
        return []
    if not shared_party_identity(addendum, base):
        return []
    return [
        f"official_council_resolution={resolution['resolution']}",
        f"official_council_resolution_date={resolution['resolution_date']}",
        f"official_council_resolution_url={resolution['url']}",
    ]


def build_links(projects):
    links, candidates = [], []
    unique_parent_bases = unique_document_parent_bases(projects)
    for i, left in enumerate(projects):
        for right in projects[i + 1:]:
            explicit_best = None
            candidate_best = None
            for sa in left.get("sources", []):
                a = sa.get("record", {})
                for sb in right.get("sources", []):
                    b = sb.get("record", {})
                    refs_a = resolver.referenced_contract_numbers(a) | resolver.related_contract_numbers(a) | set(DOCUMENT_REFS.get(str(a.get("source_id") or ""), []))
                    refs_b = resolver.referenced_contract_numbers(b) | resolver.related_contract_numbers(b) | set(DOCUMENT_REFS.get(str(b.get("source_id") or ""), []))
                    related_a = resolver.related_contract_ids(a)
                    related_b = resolver.related_contract_ids(b)
                    ida = str(a.get("source_id") or a.get("version_id") or "").strip()
                    idb = str(b.get("source_id") or b.get("version_id") or "").strip()
                    na, nb = resolver.contract_number(a), resolver.contract_number(b)
                    related_id_match = (
                        (resolver.is_addendum(a) and not resolver.is_addendum(b) and idb in related_a)
                        or (resolver.is_addendum(b) and not resolver.is_addendum(a) and ida in related_b)
                        or (ida in related_b)
                        or (idb in related_a)
                    )
                    explicit_parent = (
                        resolver.is_addendum(a) and not resolver.is_addendum(b) and (
                            any(resolver.contract_number_matches(x, nb) for x in refs_a)
                            or resolver.contract_family_matches(na, nb)
                        )
                    ) or (
                        resolver.is_addendum(b) and not resolver.is_addendum(a) and (
                            any(resolver.contract_number_matches(x, na) for x in refs_b)
                            or resolver.contract_family_matches(nb, na)
                        )
                    )
                    # A primary document can identify its original agreement by
                    # the original signing date rather than a Registry ID/number.
                    # Require matching project wording and an official shared party
                    # identifier so a common date alone cannot create a link.
                    document_parent_match = False
                    document_parent_evidence = []
                    if resolver.is_addendum(a) and not resolver.is_addendum(b):
                        addendum, base, add_id = a, b, ida
                    elif resolver.is_addendum(b) and not resolver.is_addendum(a):
                        addendum, base, add_id = b, a, idb
                    else:
                        addendum = base = None
                        add_id = ""
                    official_resolution_evidence = (
                        official_resolution_parent_evidence(addendum, base)
                        if addendum and base else []
                    )
                    if addendum and base:
                        base_date = resolver.date_value(
                            base.get("signed_date") or base.get("date") or base.get("published")
                        )
                        document_titles = DOCUMENT_PROJECT_TITLES.get(add_id, [])
                        if document_titles:
                            overlap = max(
                                resolver.meaningful_token_overlap(project_title, resolver.core_title(base))
                                for project_title in document_titles
                            )
                        else:
                            overlap = resolver.meaningful_token_overlap(
                                resolver.core_title(addendum), resolver.core_title(base)
                            )
                        date_and_party_match = (
                            base_date
                            and base_date in DOCUMENT_PARENT_DATES.get(add_id, [])
                            and shared_party_identity(addendum, base)
                        )
                        # Older municipal grant agreements may have a generic
                        # registry title without the project name. Permit that
                        # narrow case only when date + official party IDs identify
                        # exactly one possible base agreement in the supplied data.
                        candidate_base_ids = unique_parent_bases.get(add_id, set())
                        generic_unique_match = (
                            generic_base_title(base)
                            and len(candidate_base_ids) == 1
                            and str(base.get("source_id") or base.get("version_id") or "").strip()
                                in candidate_base_ids
                        )
                        if date_and_party_match and (overlap >= .65 or generic_unique_match):
                            document_parent_match = True
                            document_parent_evidence = [
                                f"document_original_contract_date={base_date}",
                                f"document_project_title_overlap={overlap:.2f}",
                            ]
                            if generic_unique_match and overlap < .65:
                                document_parent_evidence.append(
                                    "generic_base_title_unique_date_and_party_match=true"
                                )
                    explicit = (
                        related_id_match or explicit_parent or document_parent_match
                        or bool(official_resolution_evidence)
                    )
                    if explicit:
                        matching_refs = [
                            x for x in refs_a if resolver.contract_number_matches(x, nb)
                        ] + [
                            x for x in refs_b if resolver.contract_number_matches(x, na)
                        ]
                        evidence = unique_evidence(sorted(matching_refs))
                        if related_id_match:
                            related_id = idb if idb in related_a else ida
                            evidence = unique_evidence([f"related_contract_id={related_id}"] + evidence)
                        if document_parent_match:
                            evidence = unique_evidence(document_parent_evidence + evidence)
                        if official_resolution_evidence:
                            evidence = unique_evidence(official_resolution_evidence + evidence)
                        if not evidence and na and nb and resolver.contract_family_matches(na, nb):
                            evidence = unique_evidence([na, nb])
                        if related_id_match:
                            reason = "explicit_related_contract_id"
                        elif explicit_parent:
                            reason = "explicit_parent_contract_number"
                        elif "generic_base_title_unique_date_and_party_match=true" in evidence:
                            reason = "explicit_parent_contract_date_party_unique_base"
                        elif official_resolution_evidence:
                            reason = "explicit_parent_official_council_resolution"
                        else:
                            reason = "explicit_parent_contract_date_and_project"
                        item = {"kind": "contractual", "confidence": "explicit",
                                "reason": reason,
                                "evidence": evidence, "a": a, "b": b}
                        explicit_best = item
                        continue
                    # Review candidates are cross-source only. Within the
                    # Register of Contracts, explicit identifiers can confirm a
                    # relationship; fuzzy same-source pairs are overwhelmingly
                    # unrelated contracts sharing a counterparty or generic title.
                    same_source = str(a.get("source") or "").strip() == str(b.get("source") or "").strip()
                    if same_source:
                        # Same-source fuzzy pairs are normally noise. Keep one
                        # narrow exception for an addendum and an earlier base
                        # contract whose distinctive project title matches
                        # strongly. This remains a review candidate, never an
                        # automatic contractual link.
                        if resolver.is_addendum(a) != resolver.is_addendum(b):
                            # When both same-source records expose contract numbers,
                            # differing numbers are strong evidence against a fuzzy parent
                            # relationship. Keep the candidate only when the numbers belong
                            # to the same explicit family.
                            na = resolver.contract_number(a)
                            nb = resolver.contract_number(b)
                            if na and nb and not resolver.contract_family_matches(na, nb):
                                continue
                            score, reason, evidence = resolver.score(a, b)
                            da = resolver.date_value(a.get("date") or a.get("published") or a.get("signed_date") or a.get("award_date"))
                            db = resolver.date_value(b.get("date") or b.get("published") or b.get("signed_date") or b.get("award_date"))
                            base_is_earlier = (
                                (resolver.is_addendum(a) and db and da and db <= da)
                                or (resolver.is_addendum(b) and da and db and da <= db)
                            )
                            meaningful = resolver.meaningful_token_overlap(resolver.core_title(a), resolver.core_title(b))
                            if reason == "candidate_addendum_core_title" and score >= .74 and meaningful >= .65 and base_is_earlier:
                                item = {"kind": "contextual", "confidence": "review",
                                        "reason": reason, "evidence": evidence, "a": a, "b": b}
                                if candidate_best is None or score > candidate_best[0]:
                                    candidate_best = (score, item)
                        continue
                    score, reason, evidence = resolver.score(a, b)
                    if score < .60:
                        continue
                    item = {"kind": "contextual", "confidence": "strong" if score >= .82 else "review",
                            "reason": reason, "evidence": evidence, "a": a, "b": b}
                    if candidate_best is None or score > candidate_best[0]:
                        candidate_best = (score, item)

            def row(item):
                return {
                    "project_a": left["id"], "title_a": left.get("title"),
                    "project_b": right["id"], "title_b": right.get("title"),
                    "kind": item["kind"], "confidence": item["confidence"],
                    "reason": item["reason"], "evidence": item["evidence"],
                    "source_a": item["a"].get("source"), "source_id_a": item["a"].get("source_id"),
                    "source_b": item["b"].get("source"), "source_id_b": item["b"].get("source_id"),
                }
            if explicit_best:
                links.append(row(explicit_best))
            elif candidate_best:
                candidates.append(row(candidate_best[1]))

    links.sort(key=lambda x: (x["title_a"] or "", x["title_b"] or ""))
    candidates.sort(key=lambda x: (x["confidence"] != "strong", x["title_a"] or "", x["title_b"] or ""))
    return links, candidates



def build_document_bundle_links():
    """Find explicit base/addendum pairs among attachments stored in one registry record."""
    from urllib.parse import unquote

    manifest_path = DOC_MANIFEST
    contracts_path = ROOT / "data" / "registr_smluv" / "contracts.json"
    if not manifest_path.exists() or not contracts_path.exists():
        return []
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        contract_rows = json.loads(contracts_path.read_text(encoding="utf-8")).get("records", [])
    except (OSError, json.JSONDecodeError):
        return []

    records_by_id = {
        str(row.get("source_id") or "").strip(): row
        for row in contract_rows
        if str(row.get("source_id") or "").strip()
    }
    project_by_source = {}
    project_titles = {}
    for path in sorted((ROOT / "data" / "projects").glob("*.json")):
        try:
            project = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        pid = str(project.get("id") or "").strip()
        if not pid:
            continue
        project_titles[pid] = project.get("title") or project.get("canonical", {}).get("title") or pid
        for source in project.get("sources", []):
            row = source.get("record") or source
            sid = str(row.get("source_id") or source.get("source_id") or "").strip()
            if sid:
                project_by_source[sid] = pid

    def identifier_tokens(value):
        text = unquote(str(value or ""))
        found = set()
        for match in re.finditer(
            r"\bOLP\s*[/_-]?\s*(\d{1,6})\s*[/_-]\s*(\d{4})\b",
            text, flags=re.IGNORECASE,
        ):
            found.add("OLP/{}/{}".format(match.group(1), match.group(2)))
        for match in re.finditer(r"\b\d{8,12}\b", text):
            found.add(match.group(0))
        return found

    def read_document(doc):
        if doc.get("status") == "content_mismatch_review":
            return ""
        rel = doc.get("text_file")
        if not rel:
            return ""
        try:
            return (ROOT / rel).read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""

    def is_addendum(doc, body):
        name = unquote(str(doc.get("name") or "")).lower()
        compact_name = re.sub(r"[^a-z0-9]+", "", name)
        opening = re.sub(r"\s+", " ", (body or "")[:900]).strip().lower()
        compact_opening = re.sub(r"[^a-z0-9]+", "", opening)
        return (
            "dodatek" in compact_name
            or "dohodaozmene" in compact_name
            or bool(re.search(r"\b(?:dodatek\s*(?:č\.?\s*)?\d+|dohoda\s+o\s+změně\s+podmínek)\b", opening, re.IGNORECASE))
            or compact_opening.startswith("dodatek")
            or compact_opening.startswith("dohodaozmene")
        )

    relations = []
    for record in manifest.get("records", []):
        sid = str(record.get("source_id") or "").strip()
        docs = record.get("documents") or []
        if not sid or len(docs) < 2:
            continue
        loaded = []
        for doc in docs:
            body = read_document(doc)
            name = unquote(str(doc.get("name") or ""))
            identifiers = identifier_tokens(name + "\n" + body)
            loaded.append({
                "doc": doc,
                "name": name,
                "body": body,
                "identifiers": identifiers,
                "is_addendum": is_addendum(doc, body),
            })
        addenda = [item for item in loaded if item["is_addendum"]]
        bases = [item for item in loaded if not item["is_addendum"]]
        for addendum in addenda:
            matching_bases = [
                base for base in bases
                if addendum["identifiers"] & base["identifiers"]
            ]
            if len(matching_bases) != 1:
                continue
            base = matching_bases[0]
            shared = sorted(addendum["identifiers"] & base["identifiers"])
            if not shared:
                continue
            pid = project_by_source.get(sid)
            if not pid:
                continue
            base_doc, addendum_doc = base["doc"], addendum["doc"]
            relations.append({
                "project_id": pid,
                "project_title": project_titles.get(pid, record.get("title") or sid),
                "source_id": sid,
                "source_title": record.get("title") or records_by_id.get(sid, {}).get("title") or sid,
                "source_url": record.get("page_url") or records_by_id.get(sid, {}).get("detail_url") or records_by_id.get(sid, {}).get("source_url"),
                "kind": "document_bundle",
                "confidence": "explicit",
                "reason": "same_registry_record_explicit_parent_reference",
                "base_document_name": base["name"],
                "base_document_url": base_doc.get("url"),
                "base_document_text_available": bool(base["body"]),
                "addendum_document_name": addendum["name"],
                "addendum_document_url": addendum_doc.get("url"),
                "addendum_document_text_available": bool(addendum["body"]),
                "evidence": [
                    "same_registry_record=true",
                    "shared_contract_identifier={}".format(shared[0]),
                    "base_and_addendum_are_separate_attachments=true",
                ],
            })

    relations.sort(key=lambda row: (row["project_title"], row["addendum_document_name"]))
    return relations


def main():
    projects = []
    for path in sorted((ROOT / "data" / "projects").glob("*.json")):
        try:
            projects.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            continue
    links, candidates = build_links(projects)
    document_links = build_document_bundle_links()
    output = {"count": len(links), "links": links,
              "candidate_count": len(candidates), "candidates": candidates,
              "document_link_count": len(document_links), "document_links": document_links}
    (ROOT / "data" / "contract_links.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Built {len(links)} explicit contractual links, {len(candidates)} review candidates, and {len(document_links)} bundled-document links across {len(projects)} projects.")


if __name__ == "__main__":
    main()
