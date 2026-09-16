#!/usr/bin/env python3
"""Derive neutral, auditable control signals and timelines from projects."""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECTS = ROOT / "data" / "projects"


def num(v):
    if v in (None, ""):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).replace("\xa0", "").replace("Kč", "").replace("CZK", "").strip()
    try:
        if "," in s and "." in s:
            if s.rfind(",") > s.rfind("."):
                s = s.replace(".", "").replace(",", ".")
            else:
                s = s.replace(",", "")
        else:
            s = s.replace(",", ".")
        return float(re.search(r"-?\d+(?:\.\d+)?", s).group(0))
    except (AttributeError, ValueError):
        return None


def date_value(v):
    if not v:
        return None
    s = str(v).strip()
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        try:
            return date(*map(int, m.groups()))
        except ValueError:
            return None
    m = re.match(r"^(\d{2})\.(\d{2})\.(\d{4})", s)
    if m:
        try:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            return None
    return None


def field(r, *names):
    for n in names:
        if r.get(n) not in (None, ""):
            return r[n]
    return None


def event_type(r):
    text = " ".join(str(r.get(k, "")) for k in ("event", "type", "title", "subject", "last_version")).lower()
    if any(x in text for x in ("dodatek", "změnový list", "zmenovy list", "change order")):
        return "addendum"
    if any(x in text for x in ("výsledek", "vysledek", "výběr", "vyber", "oznámení o výběru", "award")):
        return "award"
    if any(x in text for x in ("smlouva", "contract")):
        return "contract"
    if any(x in text for x in ("veřejná zakázka", "verejna zakazka", "zakázka", "zakazka", "tender")):
        return "tender"
    return "source_record"


def analyze(project):
    rows = [s.get("record", {}) for s in project.get("sources", [])]
    timeline = []
    suppliers = set()
    docs = []
    deadlines = []
    scopes = []

    for r in rows:
        p = num(field(r, "price", "contract_price", "winning_bid", "value"))
        d = date_value(field(r, "date", "published", "signed_date", "award_date"))
        s = field(r, "supplier_ico", "ico_dodavatele")
        if s:
            suppliers.add(str(s))
        if isinstance(r.get("documents"), list):
            docs.extend(r["documents"])
        deadline = field(r, "deadline", "completion_deadline", "term", "end_date", "deadline_date")
        if deadline:
            deadlines.append({"date": date_value(deadline), "raw": str(deadline), "source_id": r.get("source_id")})
        scope = field(r, "scope", "subject_description", "description", "scope_change")
        if scope:
            scopes.append({"value": str(scope), "source_id": r.get("source_id")})
        timeline.append({
            "date": d.isoformat() if d else None,
            "event": event_type(r),
            "source": r.get("source"),
            "source_id": r.get("source_id"),
            "title": r.get("title") or r.get("subject"),
            "price": p,
            "deadline": date_value(deadline).isoformat() if date_value(deadline) else None,
        })

    timeline.sort(key=lambda x: (x["date"] is None, x["date"] or "", x["event"]))
    priced = [x for x in timeline if x["price"] is not None]
    unique_prices = []
    for x in priced:
        if x["price"] not in unique_prices:
            unique_prices.append(x["price"])

    baseline = next((x["price"] for x in priced if x["event"] in ("contract", "award")), None)
    if baseline is None and priced:
        baseline = priced[0]["price"]
    current = priced[-1]["price"] if priced else None

    signals = []

    def add(code, level, message, evidence=None):
        signals.append({"code": code, "level": level, "message": message, "evidence": evidence or []})

    price_change_pct = None
    if baseline is not None and current is not None and baseline != 0 and len(unique_prices) >= 2:
        price_change_pct = (current - baseline) / baseline * 100
        add("price_change", "review" if abs(price_change_pct) >= 10 else "watch",
            f"Mezi výchozí a poslední evidovanou cenou je rozdíl {price_change_pct:+.1f} %.",
            [{"type": "price_change", "baseline": baseline, "current": current,
              "delta": current - baseline, "percent": price_change_pct,
              "calculation": "(current-baseline)/baseline*100"}])

    addenda = [x for x in timeline if x["event"] == "addendum"]
    if addenda:
        add("addendum_count", "info", f"Ve zdrojových záznamech bylo rozpoznáno {len(addenda)} dodatků / změnových záznamů.",
            [{"type": "count", "value": len(addenda)}])

    if len(suppliers) > 1:
        add("supplier_difference", "review",
            "Mezi zdroji se objevilo více různých IČO dodavatele; záznam vyžaduje kontrolu propojení.",
            [{"type": "supplier_icos", "values": sorted(suppliers)}])

    dated_events = [x for x in timeline if x["date"]]
    for left, right in zip(dated_events, dated_events[1:]):
        a, b = date_value(left["date"]), date_value(right["date"])
        gap = (b - a).days
        if left["event"] == "contract" and right["event"] == "addendum" and 0 <= gap <= 7:
            add("addendum_timing", "watch",
                "Dodatek byl podle dostupných dat zaznamenán do 7 dnů od smlouvy; ověřit dokumentaci a data podpisu/zveřejnění.",
                [{"type": "days_after_contract", "value": gap,
                  "contract_source_id": left["source_id"], "addendum_source_id": right["source_id"]}])

    known_deadlines = [x for x in deadlines if x["date"]]
    if len({x["date"] for x in known_deadlines}) > 1:
        vals = [x["date"].isoformat() for x in known_deadlines]
        add("deadline_change", "watch",
            "Ve zdrojových datech byly nalezeny různé termíny dokončení/plnění; ověřit, zda jde o změnu smluvního termínu.",
            [{"type": "deadline_values", "values": vals}])

    if len(scopes) > 1:
        normalized = {re.sub(r"\s+", " ", x["value"].strip().lower()) for x in scopes}
        if len(normalized) > 1:
            add("scope_difference", "watch",
                "Mezi zdrojovými záznamy se liší popis předmětu/rozsahu; může jít o rozdílné zdrojové verze a vyžaduje kontrolu.",
                [{"type": "scope_values", "values": scopes}])

    if not rows:
        add("missing_source_record", "review", "Projekt nemá dostupný zdrojový záznam.")
    elif len(rows) == 1:
        add("single_source", "info", "Projekt je zatím doložen pouze jedním zdrojovým záznamem.")

    return {
        "schema_version": 4,
        "project_id": project.get("id"),
        "signal_count": len(signals),
        "signals": signals,
        "timeline": timeline,
        "financial": {"baseline_price": baseline, "current_observed_price": current,
                      "absolute_change": (current - baseline) if baseline is not None and current is not None else None,
                      "percent_change": price_change_pct, "observed_prices": unique_prices,
                      "addendum_count": len(addenda)},
        "metrics": {"source_count": len(rows), "supplier_count": len(suppliers),
                     "price_values": unique_prices,
                     "date_values": sorted({x["date"] for x in timeline if x["date"]}),
                     "document_count": len(docs), "deadline_observations": len(known_deadlines)},
        "methodology": "Signals are descriptive checks only; they do not establish wrongdoing or causality. They identify differences worth checking and retain source provenance.",
    }


def main():
    count = 0
    for p in sorted(PROJECTS.glob("*.json")):
        project = json.loads(p.read_text(encoding="utf-8"))
        project["analysis"] = analyze(project)
        p.write_text(json.dumps(project, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        count += 1
    print(f"Analyzed {count} projects.")


if __name__ == "__main__":
    main()
