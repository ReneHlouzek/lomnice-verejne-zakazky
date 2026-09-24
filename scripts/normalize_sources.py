#!/usr/bin/env python3
"""Normalize acquired official-source records into data/sources/."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUYER_ICO = "00275905"
OUT = ROOT / "data" / "sources"
RS = ROOT / "data" / "registr_smluv" / "contracts.json"
VU_SEED = ROOT / "data" / "inbox" / "vu_seed.json"
VU_ENRICHMENT = ROOT / "data" / "inbox" / "vu_enrichment_2026-09-22.json"
VU_XML_ENRICHMENT = ROOT / "data" / "inbox" / "vu_xml_enrichment.json"


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
    s = str(v).replace("\xa0", "").replace("Kč", "").replace("CZK", "").replace(" ", "")
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
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    return float(m.group(0)) if m else None


def date_value(v):
    s = clean(v)
    if not s:
        return None
    # XMLdataVZ uses ISO timestamps with timezone offsets; normalize them
    # to a plain local calendar date before the site consumes the value.
    iso_candidate = s.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(iso_candidate).date().isoformat()
    except ValueError:
        pass
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
    if not isinstance(rows, list):
        rows = []
    target = OUT / "registr-smluv"
    target.mkdir(parents=True, exist_ok=True)
    for old in target.glob("*.json"):
        old.unlink()
    count = 0
    for i, r in enumerate(rows, 1):
        if not isinstance(r, dict):
            continue
        if r.get("source") not in (None, "registr-smluv") and not r.get("title"):
            continue
        detail = clean(r.get("detail_url") or r.get("source_url"))
        record = {
            "source": "registr-smluv",
            "source_id": clean(r.get("source_id")) or detail or f"rs-{i:06d}",
            "version_id": clean(r.get("version_id")),
            "source_url": detail,
            "title": clean(r.get("title") or r.get("subject")),
            "buyer_ico": BUYER_ICO,
            "supplier_ico": ico(r.get("supplier_ico")),
            "supplier_name": clean(r.get("counterparty") or r.get("supplier_name")),
            "contract_number": clean(r.get("contract_number")),
            "date": date_value(r.get("signed_date") or r.get("published") or r.get("date")),
            "signed_date": date_value(r.get("signed_date")),
            "published": date_value(r.get("published")),
            "price": price(r.get("price") or r.get("value")),
            "status": clean(r.get("status")),
            "raw": r,
        }
        (target / f"rs-{count + 1:06d}.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        count += 1
    return count


def merge_rows(base_rows, extra_rows):
    merged = list(base_rows)

    def key(r):
        sid = clean(r.get("source_id") or r.get("procurement_id"))
        if sid:
            return ("id", sid)
        return ("text", clean(r.get("source_url")), clean(r.get("title")), clean(r.get("date")))

    positions = {key(r): i for i, r in enumerate(merged) if isinstance(r, dict)}
    for r in extra_rows:
        if not isinstance(r, dict) or not clean(r.get("title")):
            continue
        k = key(r)
        if k in positions:
            base = dict(merged[positions[k]])
            base.update({kk: vv for kk, vv in r.items() if vv not in (None, "")})
            merged[positions[k]] = base
        else:
            positions[k] = len(merged)
            merged.append(r)
    return merged


def normalize_vu_seed():
    if not VU_SEED.exists():
        return 0, 0, 0

    rows = json.loads(VU_SEED.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        return 0, 0, 0

    if VU_XML_ENRICHMENT.exists():
        extra = json.loads(VU_XML_ENRICHMENT.read_text(encoding="utf-8"))
        if isinstance(extra, list):
            rows = merge_rows(rows, extra)

    if VU_ENRICHMENT.exists():
        extra = json.loads(VU_ENRICHMENT.read_text(encoding="utf-8"))
        if isinstance(extra, list):
            rows = merge_rows(rows, extra)

    target = OUT / "vhodne-uverejneni"
    target.mkdir(parents=True, exist_ok=True)
    for old in target.glob("*.json"):
        old.unlink()

    count = 0
    verified_count = 0
    xml_count = 0
    for r in rows:
        if not isinstance(r, dict) or not clean(r.get("title")):
            continue
        verification_level = clean(r.get("verification_level"))
        official_xml_available = bool(r.get("xml_file") or r.get("xml_documents") or verification_level == "official_xml")
        record = {
            "source": "vhodne-uverejneni",
            "source_id": clean(r.get("source_id") or r.get("procurement_id")) or (
                "vu-" + hashlib.sha1(clean(r.get("source_url") or r.get("title") or "").encode("utf-8")).hexdigest()[:12]
            ),
            "procurement_id": clean(r.get("procurement_id")),
            "source_url": clean(r.get("source_url")),
            "title": clean(r.get("title")),
            "buyer_ico": BUYER_ICO,
            "supplier_ico": ico(r.get("supplier_ico")),
            "supplier_name": clean(r.get("supplier_name")),
            "date": date_value(r.get("date")),
            "price": price(r.get("price")),
            "expected_value": price(r.get("expected_value")),
            "price_vat_included": price(r.get("price_vat_included")),
            "status": clean(r.get("status")),
            "type": clean(r.get("type")),
            "procurement_regime": clean(r.get("procurement_regime")),
            "procurement_procedure": clean(r.get("procurement_procedure")),
            "procurement_type": clean(r.get("procurement_type")),
            "outcome": clean(r.get("outcome")),
            "description": clean(r.get("description")),
            "cpv": r.get("cpv") if isinstance(r.get("cpv"), list) else [],
            "offer_deadline": clean(r.get("offer_deadline")),
            "contract_signed_date": clean(r.get("contract_signed_date")),
            "award_date": clean(r.get("award_date")),
            "participant_count": r.get("participant_count") if isinstance(r.get("participant_count"), int) else None,
            "bid_count": r.get("bid_count") if isinstance(r.get("bid_count"), int) else None,
            "funded": r.get("funded"),
            "grant_id": clean(r.get("grant_id")),
            "project_registry_id": clean(r.get("project_registry_id")),
            "known_addenda_numbers": r.get("known_addenda_numbers") if isinstance(r.get("known_addenda_numbers"), list) else [],
            "document_count": r.get("document_count") if isinstance(r.get("document_count"), int) else None,
            "verification_level": verification_level,
            "official_xml_available": official_xml_available,
            "verified_web": bool(r.get("verified_web")) and verification_level != "official_xml",
            "verified_at": clean(r.get("verified_at")),
            "verification_source": clean(r.get("verification_source")),
            "xml_documents": r.get("xml_documents") if isinstance(r.get("xml_documents"), list) else [],
            "xml_file": clean(r.get("xml_file")),
            "raw": r,
        }
        (target / f"vu-{count + 1:06d}.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        count += 1
        if record["verified_web"]:
            verified_count += 1
        if official_xml_available:
            xml_count += 1

    return count, verified_count, xml_count


def main():
    count = normalize_rs()
    vu_count, vu_verified_count, vu_xml_count = normalize_vu_seed()
    if RS.exists() and count == 0:
        raise SystemExit("Registr smluv normalization produced zero records.")
    if VU_SEED.exists() and vu_count == 0:
        raise SystemExit("VU seed exists but normalization produced zero records.")

    manifest = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "buyer_ico": BUYER_ICO,
        "registr_smluv_records": count,
        "vhodne_uverejneni_seed_records": vu_count,
        "vhodne_uverejneni_verified_web_records": vu_verified_count,
        "vhodne_uverejneni_official_xml_records": vu_xml_count,
        "sources": ["registr-smluv", "vhodne-uverejneni-seed", "vhodne-uverejneni-enrichment", "vhodne-uverejneni-xml"],
        "vhodne_uverejneni_enrichment_records": len(json.loads(VU_ENRICHMENT.read_text(encoding="utf-8"))) if VU_ENRICHMENT.exists() else 0,
        "vhodne_uverejneni_xml_records": len(json.loads(VU_XML_ENRICHMENT.read_text(encoding="utf-8"))) if VU_XML_ENRICHMENT.exists() else 0,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Normalized {count} Registr smluv records and {vu_count} VU records ({vu_verified_count} web-verified, {vu_xml_count} official-XML).")


if __name__ == "__main__":
    main()
