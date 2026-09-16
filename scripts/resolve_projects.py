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
    try:
        s = str(v).replace("\xa0", "").replace(" ", "").replace("CZK", "").replace("Kc", "")
        if "," in s and "." in s:
            if s.rfind(",") > s.rfind("."):
                s = s.replace(".", "").replace(",", ".")
            else:
                s = s.replace(",", "")
        elif "," in s:
            s = s.replace(",", ".")
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
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", s)
    return m.group(0) if m else None


def records():
    if not SOURCES.exists():
        return []
    out = []
    for p in SOURCES.rglob("*.json"):
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        rows = obj if isinstance(obj, list) else obj.get("records", [obj])
        for r in rows:
            if isinstance(r, dict):
                r = dict(r)
                r["_source_file"] = str(p.relative_to(ROOT))
                out.append(r)
    for p in SOURCES.rglob("*.jsonl"):
        for line in p.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
                r["_source_file"] = str(p.relative_to(ROOT))
                out.append(r)
            except Exception:
                pass
    return [r for r in out if ico(r.get("buyer_ico") or r.get("ico_zadavatele")) in ("", BUYER_ICO)]


def key_ids(r):
    return {str(r.get(k)).strip() for k in ("vvz_id", "vvz_identifier", "profile_id", "procurement_id", "contract_id", "contract_number") if r.get(k)}


def score(a, b):
    common = key_ids(a) & key_ids(b)
    if common:
        return 1.0, "exact_identifier", sorted(common)
    ai = ico(a.get("supplier_ico") or a.get("ico_dodavatele"))
    bi = ico(b.get("supplier_ico") or b.get("ico_dodavatele"))
    at = norm(a.get("title") or a.get("nazev") or a.get("name"))
    bt = norm(b.get("title") or b.get("nazev") or b.get("name"))
    sim = SequenceMatcher(None, at, bt).ratio() if at and bt else 0
    ap = price(a.get("price") or a.get("contract_price") or a.get("value"))
    bp = price(b.get("price") or b.get("contract_price") or b.get("value"))
    same_supplier = bool(ai and bi and ai == bi)
    near_price = bool(ap is not None and bp is not None and (abs(ap - bp) / max(ap, bp) <= .03))
    if same_supplier and sim >= .72 and (near_price or ap is None or bp is None):
        return .9, "supplier_title", [ai]
    if sim >= .86 and near_price:
        return .82, "title_price", []
    if same_supplier and sim >= .60:
        return .65, "candidate_supplier_title", [ai]
    return 0, "none", []


def classify(r):
    text = norm(" ".join(str(r.get(k) or "") for k in ("title", "name", "type", "event", "status")))
    if any(x in text for x in ("dodatek", "zmenovy list", "change order")):
        return "addendum"
    if any(x in text for x in ("smlouva", "contract")):
        return "contract"
    if any(x in text for x in ("vysledek", "vyber", "award", "oznameni o vyberu")):
        return "award"
    if any(x in text for x in ("zakazka", "verejna zakazka", "tender")):
        return "tender"
    return "source_record"


def canonical(g):
    titles = [r.get("title") or r.get("nazev") or r.get("name") for r in g if r.get("title") or r.get("nazev") or r.get("name")]
    suppliers = [r.get("supplier_ico") or r.get("ico_dodavatele") for r in g if r.get("supplier_ico") or r.get("ico_dodavatele")]
    events = []
    for r in g:
        d = date_value(r.get("date") or r.get("published") or r.get("datum") or r.get("signed_date") or r.get("award_date"))
        if d:
            events.append({"date": d, "type": classify(r), "source": r.get("source"), "source_id": r.get("source_id"), "title": r.get("title") or r.get("nazev"), "price": price(r.get("price") or r.get("contract_price") or r.get("value"))})
    events.sort(key=lambda x: x["date"])
    ids = sorted(set().union(*(key_ids(r) for r in g)))
    contract_events = [e for e in events if e["type"] in ("contract", "addendum") and e["price"] is not None]
    observed_prices = [e["price"] for e in contract_events]
    return {
        "title": max(titles, key=len) if titles else None,
        "supplier_ico": next((ico(x) for x in suppliers if ico(x)), None),
        "identifiers": ids,
        "lifecycle": {"events": events, "event_count": len(events)},
        "dates": {"first_observed": events[0]["date"] if events else None, "last_observed": events[-1]["date"] if events else None},
        "financial": {"observed_prices": sorted(set(observed_prices)), "initial_contract_price": observed_prices[0] if observed_prices else None, "latest_observed_price": observed_prices[-1] if observed_prices else None},
        "source_count": len(g),
    }


def group_score(record, group):
    """Compare a record with every member of a group and retain the strongest evidence."""
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
    for i, g in enumerate(groups, 1):
        base = g[0]
        title = base.get("title") or base.get("nazev") or base.get("name") or f"Projekt {i}"
        pid = "p-" + re.sub(r"[^a-z0-9]+", "-", norm(title))[:70].strip("-") + f"-{i:04d}"
        sources = [{"source_file": r.get("_source_file"), "source_id": r.get("source_id") or r.get("vvz_id") or r.get("contract_id"), "record": r} for r in g]
        project = {"id": pid, "title": title, "buyer_ico": BUYER_ICO, "status": "unclassified", "canonical": canonical(g), "sources": sources}
        (OUT / f"{pid}.json").write_text(json.dumps(project, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for i, a in enumerate(rows):
        for b in rows[i + 1:]:
            if a.get("_source_file") == b.get("_source_file"):
                continue
            s, reason, evidence = score(a, b)
            if .60 <= s < .82:
                candidates.append({"score": s, "reason": reason, "evidence": evidence, "a": a, "b": b})
    (ROOT / "data" / "link_candidates.json").write_text(json.dumps(candidates, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Resolved {len(rows)} source records into {len(groups)} projects; {len(candidates)} candidates for review.")


if __name__ == "__main__":
    main()
