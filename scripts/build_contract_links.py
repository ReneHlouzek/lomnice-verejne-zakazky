"""Build an explainable register of contractual links and review candidates."""
from __future__ import annotations
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import resolve_projects as resolver


def build_links(projects):
    links, candidates = [], []
    for i, left in enumerate(projects):
        for right in projects[i + 1:]:
            explicit_best = None
            candidate_best = None
            for sa in left.get("sources", []):
                a = sa.get("record", {})
                for sb in right.get("sources", []):
                    b = sb.get("record", {})
                    refs_a = resolver.referenced_contract_numbers(a)
                    refs_b = resolver.referenced_contract_numbers(b)
                    na, nb = resolver.contract_number(a), resolver.contract_number(b)
                    explicit = (
                        resolver.is_addendum(a) and (
                            any(resolver.contract_number_matches(x, nb) for x in refs_a)
                            or resolver.contract_family_matches(na, nb)
                        )
                    ) or (
                        resolver.is_addendum(b) and (
                            any(resolver.contract_number_matches(x, na) for x in refs_b)
                            or resolver.contract_family_matches(nb, na)
                        )
                    )
                    if explicit:
                        item = {"kind": "contractual", "confidence": "explicit",
                                "reason": "explicit_parent_contract_number",
                                "evidence": sorted(set(refs_a + refs_b)), "a": a, "b": b}
                        explicit_best = item
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


def main():
    projects = []
    for path in sorted((ROOT / "data" / "projects").glob("*.json")):
        try:
            projects.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            continue
    links, candidates = build_links(projects)
    output = {"count": len(links), "links": links,
              "candidate_count": len(candidates), "candidates": candidates}
    (ROOT / "data" / "contract_links.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Built {len(links)} explicit contractual links and {len(candidates)} review candidates across {len(projects)} projects.")


if __name__ == "__main__":
    main()
