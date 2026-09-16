#!/usr/bin/env python3
"""Normalize acquired official-source records into data/sources/.

The normalizer is intentionally lossless: source-specific raw data stays in its
original archive while this layer creates a small common record used for
cross-source reconciliation. Records are never linked or merged here.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUYER_ICO = "00275905"
OUT = ROOT / "data" / "sources"
RS = ROOT / "data" / "registr_smluv" / "contracts.json"


def clean(v):
    if v is None:
        return None
    s = re.sub(r"\s+", " ", str(v)).strip()
    return s or None


def ico(v):
    digits = re.sub(r"\D", "", str(v or ""))
    return digits if len(digits) == 8 else None


def price(v):
    if v in (None, ""):
        return None
    s = str(v).replace("Kč", "").replace("CZK", "").replace(" ", "")
    # Czech thousands separators and decimal commas are common in the register.
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    else:
        s = s.replace(",", ".")
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    return float(m.group(0)) if m else None


def date_value(v):
    s = clean(v)
    if not s:
        return None
    # Preserve the original text if it is not unambiguously parseable.
    for fmt in ("%d.%m.%Y", "%d. %m. %Y", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            pass
    return s


def normalize_rs():
    if not RS.exists():
        return 0
    payload = json.loads(RS.read_text(encoding="utf-8"))
    rows = payload.get("records", [])
    target = OUT / "registr-smluv"
    target.mkdir(parents=True, exist_ok=True)
    for old in target.glob("*.json"):
        old.unlink()

    count = 0
    for i, r in enumerate(rows, 1):
        detail = clean(r.get("detail_url"))
        record = {
            "source": "registr-smluv",
            "source_id": detail or f"rs-{i:06d}",
            "source_url": detail,
            "title": clean(r.get("subject")),
            "buyer_ico": BUYER_ICO,
            "supplier_ico": ico(r.get("counterparty")),
            "contract_number": clean(r.get("contract_number")),
            "date": date_value(r.get("published")),
            "price": price(r.get("value")),
            "status": clean(r.get("status")),
            "raw": r,
        }
        fn = target / f"rs-{i:06d}.json"
        fn.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        count += 1
    return count


def main():
    count = normalize_rs()
    manifest = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "buyer_ico": BUYER_ICO,
        "registr_smluv_records": count,
        "sources": ["registr-smluv"],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Normalized {count} Registr smluv records into {OUT / 'registr-smluv'}")


if __name__ == "__main__":
    main()
