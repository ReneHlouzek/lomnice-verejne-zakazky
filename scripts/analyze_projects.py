#!/usr/bin/env python3
"""Derive neutral, auditable control signals from resolved procurement projects."""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECTS = ROOT / "data" / "projects"


def num(v):
    try:
        return float(v) if v not in (None, "") else None
    except (TypeError, ValueError):
        return None


def date_value(v):
    if not v:
        return None
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", str(v))
    if not m:
        return None
    try:
        return date(*map(int, m.groups()))
    except ValueError:
        return None


def field(r, *names):
    for n in names:
        if r.get(n) not in (None, ""):
            return r[n]
    return None


def analyze(project):
    rows = [s.get("record", {}) for s in project.get("sources", [])]
    prices = []
    dates = []
    suppliers = set()
    docs = []
    for r in rows:
        p = num(field(r, "price", "contract_price", "winning_bid", "value"))
        if p is not None:
            prices.append(p)
        d = date_value(field(r, "date", "published", "signed_date", "award_date"))
        if d:
            dates.append(d)
        s = field(r, "supplier_ico", "ico_dodavatele")
        if s:
            suppliers.add(str(s))
        for d in r.get("documents", []) if isinstance(r.get("documents"), list) else []:
            docs.append(d)

    signals = []
    def add(code, level, message, evidence=None):
        signals.append({"code": code, "level": level, "message": message, "evidence": evidence or []})

    unique_prices = sorted(set(prices))
    if len(unique_prices) >= 2:
        initial, current = unique_prices[0], unique_prices[-1]
        if initial and current != initial:
            pct = (current - initial) / initial * 100
            add("price_change", "review" if abs(pct) >= 10 else "watch",
                f"Zachycen rozdíl mezi evidovanou nejnižší a nejvyšší cenou {pct:+.1f} %.",
                [{"type": "price", "values": unique_prices, "calculation": "(max-min)/min*100"}])

    if len(suppliers) > 1:
        add("supplier_difference", "review",
            "Mezi zdroji se objevilo více různých IČO dodavatele; záznam vyžaduje kontrolu propojení.",
            [{"type": "supplier_icos", "values": sorted(suppliers)}])

    if dates and dates != sorted(dates):
        add("date_order_anomaly", "review",
            "Datumy ve zdrojových záznamech nejsou v chronologickém pořadí.",
            [{"type": "dates", "values": [d.isoformat() for d in dates]}])

    if not rows:
        add("missing_source_record", "review", "Projekt nemá dostupný zdrojový záznam.")

    return {
        "schema_version": 1,
        "project_id": project.get("id"),
        "signal_count": len(signals),
        "signals": signals,
        "metrics": {
            "source_count": len(rows),
            "supplier_count": len(suppliers),
            "price_values": unique_prices,
            "date_values": sorted(d.isoformat() for d in dates),
            "document_count": len(docs),
        },
        "methodology": "Signals are descriptive checks only; they do not establish wrongdoing or causality.",
    }


def main():
    count = 0
    for p in sorted(PROJECTS.glob("*.json")):
        project = json.loads(p.read_text(encoding="utf-8"))
        analysis = analyze(project)
        project["analysis"] = analysis
        p.write_text(json.dumps(project, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        count += 1
    print(f"Analyzed {count} projects.")


if __name__ == "__main__":
    main()
