"""Resolve procurement records from official sources into unified projects."""
from __future__ import annotations

import json, re, unicodedata
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "data" / "sources"
OUT = ROOT / "data" / "projects"
BUYER_ICO = "00275905"


def norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def ico(v):
    return re.sub(r"\D", "", str(v or ""))


def price(v):
    if v in (None, ""):
        return None
    s = str(v).strip().replace("\xa0", "")
    s = re.sub(r"(?:Kč|CZK|Kc)", "", s, flags=re.I).strip()
    s = re.sub(r"[^0-9,.-]", "", s)
    if not s or s in {"-", ".", ","}:
        return None
    try:
        if "," in s and "." in s:
            if s.rfind(",") > s.rfind("."):
                s = s.replace(".", "").replace(",", ".")
            else:
                s = s.replace(",", "")
        elif "," in s:
            parts = s.split(",")
            if len(parts) > 2:
                s = "".join(parts)
            elif len(parts) == 2 and len(parts[1]) == 3 and len(parts[0]) <= 3:
                s = "".join(parts)
            else:
                s = ".".join(parts)
        elif "." in s:
            parts = s.split(".")
            if len(parts) > 2 or (len(parts) == 2 and len(parts[1]) == 3 and len(parts[0]) <= 3):
                s = "".join(parts)
        return float(s)
    except (ValueError, TypeError):
        return None


def date_value(v):
    if not v:
        return None
    s = str(v).strip()
    for fmt in ("%d.%m.%Y", "%d.%m.%Y %H:%M", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            pass
    m = re.match(r"^(\d{4}-\d{2}-\d{2})", s)
    return m.group(1) if m else None


def title(r):
    return str(r.get("title") or r.get("nazev") or r.get("name") or r.get("subject") or "").strip()


def records():
    """Read only actual normalized source records; metadata manifests are not records."""
    if not SOURCES.exists():
        return []
    out = []
    for p in SOURCES.rglob("*.json"):
        if p.name == "manifest.json":
            continue
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        rows = obj if isinstance(obj, list) else obj.get("records", [obj])
        for r in rows:
            if not isinstance(r, dict) or not title(r):
                continue
            r = dict(r)
            r["_source_file"] = str(p.relative_to(ROOT))
            out.append(r)
    for p in SOURCES.rglob("*.jsonl"):
        for line in p.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
            except Exception:
                continue
            if not isinstance(r, dict) or not title(r):
                continue
            r["_source_file"] = str(p.relative_to(ROOT))
            out.append(r)
    return [r for r in out if ico(r.get("buyer_ico") or r.get("ico_zadavatele")) in ("", BUYER_ICO)]


def key_ids(r):
    return {str(r.get(k)).strip() for k in ("vvz_id", "vvz_identifier", "profile_id", "procurement_id", "contract_id") if r.get(k)}


def contract_number(r):
    return str(r.get("contract_number") or r.get("cislo_smlouvy") or "").strip()


def is_addendum(r):
    return bool(re.search(r"\b(dodatek|dodatek c|zmenovy list|change order)\b", norm(title(r))))


def core_title(r):
    t = norm(title(r))
    t = re.sub(r"\bdodatek(?: c)?\s*\d*\b", " ", t)
    t = re.sub(r"\bzmenovy list(?: c)?\s*\d*\b", " ", t)
    t = re.sub(r"\bke smlouve\b", " smlouva ", t)
    t = re.sub(r"\bke smlouve o dilo\b", " smlouva o dilo ", t)
    return re.sub(r"\s+", " ", t).strip()


def score(a, b):
    common = key_ids(a) & key_ids(b)
    if common:
        return 1.0, "exact_identifier", sorted(common)

    an = contract_number(a)
    bn = contract_number(b)
    if an and bn and an != bn:
        # Different explicit contract numbers are strong evidence against merging.
        return 0, "different_contract_number", [an, bn]

    ai = ico(a.get("supplier_ico") or a.get("ico_dodavatele"))
    bi = ico(b.get("supplier_ico") or b.get("ico_dodavatele"))
    at = norm(title(a))
    bt = norm(title(b))
    act = core_title(a)
    bct = core_title(b)
    sim = SequenceMatcher(None, at, bt).ratio() if at and bt else 0
    core_sim = SequenceMatcher(None, act, bct).ratio() if act and bct else 0
    ap = price(a.get("price") or a.get("contract_price") or a.get("value"))
    bp = price(b.get("price") or b.get("contract_price") or b.get("value"))
    same_supplier = bool(ai and bi and ai == bi)
    near_price = bool(ap is not None and bp is not None and (abs(ap - bp) / max(ap, bp) <= .03))
    addendum_pair = is_addendum(a) != is_addendum(b)

    # Auto-merge only when the evidence is sufficiently specific. A generic
    # title + same supplier is not enough: one supplier can have many unrelated
    # contracts with very similar legal wording.
    if addendum_pair and same_supplier and core_sim >= .82 and (near_price or ap is None or bp is None):
        return .96, "addendum_core_title", [ai]
    if same_supplier and sim >= .82 and near_price:
        return .9, "supplier_title_price", [ai]
    if sim >= .9 and near_price:
        return .82, "title_price", []
    if addendum_pair and same_supplier and core_sim >= .68:
        return .74, "candidate_addendum_core_title", [ai]
    if same_supplier and sim >= .66 and near_price:
        return .74, "candidate_supplier_title_price", [ai]
    if same_supplier and sim >= .60:
        return .65, "candidate_supplier_title", [ai]
    return 0, "none", []


def classify(r):
    text = norm(" ".join(str(r.get(k) or "") for k in ("title", "name", "type", "event", "status")))
    if any(x in text for x in ("dodatek", "zmenovy list", "change order")):
        return "addendum"
    if any(x in text for x in ("vysledek", "vyber", "award", "oznameni o vyberu")):
        return "award"
    if any(x in text for x in ("verejna zakazka", "zakazka", "tender")):
        return "tender"
    if any(x in text for x in ("smlouva", "contract")):
        return "contract"
    return "source_record"



def procurement_signal(r):
    """Classify contractual text as evidence of a procurement relationship.

    This is deliberately weaker than a procurement classification: a contract
    may be related to an investment without proving how the supplier was chosen.
    """
    text = norm(" ".join(str(r.get(k) or "") for k in ("title", "name", "type", "event", "status", "subject")))
    explicit = (
        "verejna zakazka" in text or "zakazka" in text or
        "vyberove rizeni" in text or "zjednodusene podlimitni" in text or
        "vybrana nabidka" in text or "nejvhodnejsi nabidka" in text
    )
    works = any(x in text for x in (
        "smlouva o dilo", "oprava", "rekonstrukce", "sanace", "modernizace",
        "obnova", "revitalizace", "stavebni", "komunikace", "rybnik",
        "kamerovy system", "pojisteni", "dodavka"
    ))
    if explicit:
        return {"level": "explicit", "label": "Výslovná vazba na veřejnou zakázku", "reason": "Zdrojový text obsahuje přímou zmínku o veřejné zakázce, výběru nebo zadávacím řízení."}
    if works:
        return {"level": "likely", "label": "Pravděpodobně souvisí se zakázkou", "reason": "Název/předmět odpovídá investiční dodávce, stavebním pracím nebo jiné běžné zadavatelské dodávce; způsob výběru dodavatele z tohoto záznamu sám o sobě neplyne."}
    return {"level": "none", "label": "Bez rozpoznané vazby na zakázku", "reason": "V dostupném textu nebyl nalezen dostatečný signál."}

def canonical(g):
    titles = [title(r) for r in g if title(r)]
    suppliers = [r.get("supplier_ico") or r.get("ico_dodavatele") for r in g if r.get("supplier_ico") or r.get("ico_dodavatele")]
    events = []
    for r in g:
        d = date_value(r.get("date") or r.get("published") or r.get("datum") or r.get("signed_date") or r.get("award_date"))
        if d:
            events.append({"date": d, "type": classify(r), "source": r.get("source"), "source_id": r.get("source_id"), "title": title(r), "price": price(r.get("price") or r.get("contract_price") or r.get("value"))})
    events.sort(key=lambda x: x["date"])
    contract_events = [e for e in events if e["type"] in ("contract", "addendum") and e["price"] is not None]
    observed_prices = [e["price"] for e in contract_events]
    type_counts = {}
    for e in events:
        type_counts[e["type"]] = type_counts.get(e["type"], 0) + 1
    dominant_type = max(type_counts, key=type_counts.get) if type_counts else "source_record"
    has_procurement_event = bool(type_counts.get("tender") or type_counts.get("award"))
    has_addendum = bool(type_counts.get("addendum"))
    if has_procurement_event and has_addendum:
        project_type = "procurement_with_changes"
    elif has_procurement_event:
        project_type = "procurement"
    elif has_addendum:
        project_type = "contract_with_changes"
    elif type_counts.get("contract"):
        project_type = "contract"
    else:
        project_type = "other"
    return {
        "title": max(titles, key=len) if titles else None,
        "supplier_ico": next((ico(x) for x in suppliers if ico(x)), None),
        "identifiers": sorted(set().union(*(key_ids(r) for r in g))),
        "lifecycle": {"events": events, "event_count": len(events), "type_counts": type_counts, "dominant_type": dominant_type},
        "project_type": project_type,
        "procurement_signal": max((procurement_signal(r) for r in g), key=lambda x: {"none":0,"likely":1,"explicit":2}[x["level"]]),
        "dates": {"first_observed": events[0]["date"] if events else None, "last_observed": events[-1]["date"] if events else None},
        "financial": {"observed_prices": sorted(set(observed_prices)), "initial_contract_price": observed_prices[0] if observed_prices else None, "latest_observed_price": observed_prices[-1] if observed_prices else None},
        "source_count": len(g),
    }


def group_score(record, group):
    best = (0, "none", [])
    for member in group:
        current = score(record, member)
        if current[0] > best[0]:
            best = current
    return best


def main():
    rows = records()
    groups = []
    candidates = []
    for r in rows:
        best = None
        for i, g in enumerate(groups):
            s, reason, evidence = group_score(r, g)
            if s and (best is None or s > best[0]):
                best = (s, reason, evidence, i)
        if best and best[0] >= .82:
            groups[best[3]].append(r)
        else:
            groups.append([r])

    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.json"):
        old.unlink()
    audit = {"source_records": len(rows), "projects": len(groups), "project_sizes": {}, "classifications": {}, "candidate_count": 0}
    for i, g in enumerate(groups, 1):
        base = g[0]
        t = title(base)
        if not t:
            continue
        pid = "p-" + re.sub(r"[^a-z0-9]+", "-", norm(t))[:70].strip("-") + f"-{i:04d}"
        sources = [{"source_file": r.get("_source_file"), "source_id": r.get("source_id") or r.get("vvz_id") or r.get("contract_id"), "record": r} for r in g]
        can = canonical(g)
        project = {"id": pid, "title": t, "buyer_ico": BUYER_ICO, "status": "unclassified", "project_type": can["project_type"], "canonical": can, "sources": sources}
        (OUT / f"{pid}.json").write_text(json.dumps(project, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        audit["project_sizes"][pid] = len(g)
        audit["classifications"][can["project_type"]] = audit["classifications"].get(can["project_type"], 0) + 1

    for i, a in enumerate(rows):
        for b in rows[i + 1:]:
            if a.get("_source_file") == b.get("_source_file"):
                continue
            s, reason, evidence = score(a, b)
            if .60 <= s < .82:
                candidates.append({"score": s, "reason": reason, "evidence": evidence, "a": a, "b": b})
    audit["candidate_count"] = len(candidates)
    (ROOT / "data" / "link_candidates.json").write_text(json.dumps(candidates, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (ROOT / "data" / "resolution_audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Resolved {len(rows)} source records into {len(groups)} projects; {len(candidates)} candidates for review.")
    print("Classification:", json.dumps(audit["classifications"], ensure_ascii=False, sort_keys=True))


if __name__ == "__main__": main()
