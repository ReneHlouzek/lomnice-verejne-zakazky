"""Build an explainable register of contractual and contextual links between projects."""
from __future__ import annotations
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import resolve_projects as resolver


def build_links(projects):
    links = []
    for i, left in enumerate(projects):
        for right in projects[i + 1:]:
            best = None
            for sa in left.get("sources", []):
                a = sa.get("record", {})
                for sb in right.get("sources", []):
                    b = sb.get("record", {})
                    refs_a = resolver.referenced_contract_numbers(a)
                    refs_b = resolver.referenced_contract_numbers(b)
                    na, nb = resolver.contract_number(a), resolver.contract_number(b)
                    explicit = (
                        resolver.is_addendum(a) and any(resolver.contract_number_matches(x, nb) for x in refs_a)
                    ) or (
                        resolver.is_addendum(b) and any(resolver.contract_number_matches(x, na) for x in refs_b)
                    )
                    if explicit:
                        item = {"kind": "contractual", "confidence": "explicit",
                                "reason": "explicit_parent_contract_number",
                                "evidence": sorted(set(refs_a + refs_b)), "a": a, "b": b}
                    else:
                        score, reason, evidence = resolver.score(a, b)
                        if score < .60:
                            continue
                        item = {"kind": "contextual", "confidence": "strong" if score >= .82 else "review",
                                "reason": reason, "evidence": evidence, "a": a, "b": b}
                    if best is None or (item["kind"] == "contractual" and best["kind"] != "contractual") or (
                        item["kind"] == best["kind"] and item.get("confidence") == "explicit"
                    ):
                        best = item
            if best:
                links.append({
                    "project_a": left["id"], "title_a": left.get("title"),
                    "project_b": right["id"], "title_b": right.get("title"),
                    "kind": best["kind"], "confidence": best["confidence"],
                    "reason": best["reason"], "evidence": best["evidence"],
                    "source_a": best["a"].get("source"), "source_id_a": best["a"].get("source_id"),
                    "source_b": best["b"].get("source"), "source_id_b": best["b"].get("source_id"),
                })
    links.sort(key=lambda x: (x["kind"] != "contractual", x["confidence"] != "explicit",
                              x["title_a"] or "", x["title_b"] or ""))
    return links


def main():
    projects = []
    for path in sorted((ROOT / "data" / "projects").glob("*.json")):
        try:
            projects.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            continue
    links = build_links(projects)
    (ROOT / "data" / "contract_links.json").write_text(
        json.dumps({"count": len(links), "links": links}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    print(f"Built {len(links)} contractual/contextual links across {len(projects)} projects.")


if __name__ == "__main__":
    main()
