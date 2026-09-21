#!/usr/bin/env python3
"""Audit source-record completeness without changing or guessing source data. Verified seed identifiers are preserved as source metadata."""
from __future__ import annotations
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "data" / "sources"
OUT = ROOT / "data" / "source_audit.json"

def rows_for(source_dir: str):
    p = SOURCES / source_dir
    if not p.exists():
        return []
    rows = []
    for f in sorted(p.glob("*.json")):
        if f.name == "manifest.json":
            continue
        try:
            r = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(r, dict):
            rows.append(r)
    return rows

def audit_source(rows, require_status=True):
    missing_url, missing_status, missing_price, missing_id = [], [], [], []
    ids = []
    for i, r in enumerate(rows, 1):
        sid = str(r.get("source_id") or r.get("procurement_id") or "").strip()
        url = str(r.get("source_url") or "").strip()
        if not url or not url.startswith("https://"):
            missing_url.append(i)
        if require_status and not str(r.get("status") or "").strip():
            missing_status.append(i)
        if r.get("price") in (None, ""):
            missing_price.append(i)
        if not sid:
            missing_id.append(i)
        else:
            ids.append(sid)
    counts = Counter(ids)
    return {
        "records": len(rows),
        "missing_source_url": missing_url,
        "missing_status": missing_status,
        "missing_price": missing_price,
        "missing_identifier": missing_id,
        "duplicate_identifiers": sorted(k for k, v in counts.items() if v > 1),
    }

def main():
    report = {
        "schema_version": 1,
        "buyer_ico": "00275905",
        "sources": {
            "vhodne-uverejneni": audit_source(rows_for("vhodne-uverejneni"), require_status=True),
            "registr-smluv": audit_source(rows_for("registr-smluv"), require_status=False),
        },
        "methodology": [
            "Audit pouze popisuje chybějící nebo duplicitní metadata; nic nedoplňuje odhadem.",
            "Chybějící cena není chyba: některé veřejné záznamy ji nemusí obsahovat.",
            "Chybějící URL znamená, že veřejná aplikace nemá bezpečný přímý odkaz na zdrojový záznam.",
            "Duplicitní identifikátor se nepovažuje automaticky za chybu; může jít o více verzí nebo zdrojových záznamů.",
            "Registr smluv nemá v importu normalizovaný životní status; jeho absence se proto v auditu nepovažuje za chybu.",
        ],
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for name, data in report["sources"].items():
        print(name, data["records"], "records;", len(data["missing_source_url"]), "missing URL;", len(data["missing_identifier"]), "missing ID")

if __name__ == "__main__":
    main()
