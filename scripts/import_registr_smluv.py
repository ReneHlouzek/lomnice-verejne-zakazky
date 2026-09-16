#!/usr/bin/env python3
"""Import public contract metadata for Lomnice from the official Contract Register."""
from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, urljoin

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
RS = CONFIG["registr_smluv"]
BASE = RS["search_url"]
ICO = RS["publisher_ico"]
OUT = ROOT / "data" / "registr_smluv"
RAW = OUT / "raw"
SOURCE_OUT = ROOT / "data" / "sources" / "registr-smluv"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def clean(text: str | None) -> str | None:
    if text is None:
        return None
    value = re.sub(r"\s+", " ", text).strip()
    return value or None


def detail_url(href: str) -> str:
    return urljoin(BASE, href)


def build_url(offset: int) -> str:
    params = {
        "publication_date[from]": "", "publication_date[to]": "",
        "subject_name": "", "subject_box": "", "subject_idnum": ICO, "subject_address": "",
        "value_foreign[from]": "", "value_foreign[to]": "", "foreign_currency": "",
        "contract_id": "", "party_name": "", "party_box": "", "party_idnum": "", "party_address": "",
        "value_no_vat[from]": "", "value_no_vat[to]": "", "file_text": "", "version_id": "",
        "contr_num": "", "sign_date[from]": "", "sign_date[to]": "", "contract_descr": "",
        "sign_person_name": "", "value_vat[from]": "", "value_vat[to]": "", "all_versions": "0",
        # The first request must submit the detailed-search form. Subsequent
        # requests can use the result-list offset action while retaining all filters.
        "do": "detailedSearchForm-submit" if offset == 0 else "searchResultList-setOffset",
        "search": "Vyhledat" if offset == 0 else "",
        "searchResultList-offset": str(offset),
        "search_type": "0",
    }
    return f"{BASE}?{urlencode(params)}"


def parse_ico(text: str | None) -> str | None:
    if not text:
        return None
    m = re.search(r"(?:IČO|ICO)\s*[:.]?\s*(\d{8})", text, re.I)
    if m:
        return m.group(1)
    candidates = re.findall(r"(?<!\d)(\d{8})(?!\d)", text)
    return candidates[-1] if candidates else None


def parse_price(text: str | None) -> float | None:
    if not text:
        return None
    s = clean(text)
    if not s:
        return None
    s = re.sub(r"[^0-9,.-]", "", s.replace("\xa0", "").replace(" ", ""))
    if not s:
        return None
    try:
        if "," in s and "." in s:
            if s.rfind(",") > s.rfind("."):
                s = s.replace(".", "").replace(",", ".")
            else:
                s = s.replace(",", "")
        elif "," in s:
            parts = s.split(",")
            s = "".join(parts) if len(parts) > 2 or (len(parts) == 2 and len(parts[1]) == 3) else ".".join(parts)
        elif "." in s:
            parts = s.split(".")
            if len(parts) > 2 or (len(parts) == 2 and len(parts[1]) == 3):
                s = "".join(parts)
        return float(s)
    except ValueError:
        return None


def parse_page(html: bytes) -> tuple[list[dict], int | None]:
    soup = BeautifulSoup(html, "html.parser")
    records: list[dict] = []
    for row in soup.find_all("tr"):
        cells = row.find_all(["td", "th"])
        if len(cells) < 5:
            continue
        texts = [clean(c.get_text(" ", strip=True)) for c in cells]
        links = [a.get("href") for a in row.find_all("a", href=True)]
        detail = next((detail_url(h) for h in links if "detail" in h.lower() or "smlouva" in h.lower()), None)
        if not detail:
            continue
        counterparty = texts[5] if len(texts) > 5 else None
        records.append({
            "source_id": detail, "source_url": detail, "title": texts[1], "buyer_ico": ICO,
            "supplier_ico": parse_ico(counterparty), "contract_number": None,
            "date": texts[3] if len(texts) > 3 else None, "price": parse_price(texts[4] if len(texts) > 4 else None),
            "publisher": texts[0], "subject": texts[1], "last_version": texts[2] if len(texts) > 2 else None,
            "published": texts[3] if len(texts) > 3 else None, "value": texts[4] if len(texts) > 4 else None,
            "counterparty": counterparty, "detail_url": detail,
        })
    total = None
    match = re.search(r"Počet nalezn[ýy]ch záznamů\s+(\d+)", soup.get_text(" ", strip=True), re.I)
    if match:
        total = int(match.group(1))
    return records, total


def looks_like_search_form(html: bytes, records: list[dict], total: int | None) -> bool:
    if records or total is not None:
        return False
    text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True).lower()
    return "podrobné vyhledávání" in text and "vyhledané smlouvy" not in text


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True); RAW.mkdir(parents=True, exist_ok=True); SOURCE_OUT.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (compatible; Lomnice-Verejne-Zakazky/0.8; +public-data-archive)", "Accept": "text/html,application/xhtml+xml"})
    all_records: dict[str, dict] = {}; pages: list[dict] = []
    page_size = int(RS.get("page_size", 100)); max_pages = int(RS.get("max_pages", 20)); failed = False

    for page_no in range(max_pages):
        offset = page_no * page_size; url = build_url(offset); print(f"Registr smluv: {url}")
        try:
            response = session.get(url, timeout=45); response.raise_for_status()
        except requests.RequestException as exc:
            print(f"  FAILED: {exc}"); pages.append({"page": page_no, "offset": offset, "url": url, "status": "unavailable", "error": str(exc)}); failed = True; break
        data = response.content; raw_name = f"page_{page_no:04d}.html"; (RAW / raw_name).write_bytes(data)
        records, total = parse_page(data)
        if looks_like_search_form(data, records, total):
            print("  FAILED: server returned the search form instead of a result table")
            pages.append({"page": page_no, "offset": offset, "url": url, "status": "unavailable", "reason": "search_form_returned", "sha256": sha256(data), "bytes": len(data), "records": 0, "total": None, "file": str((RAW / raw_name).relative_to(ROOT))}); failed = True; break
        pages.append({"page": page_no, "offset": offset, "url": url, "status": "ok", "sha256": sha256(data), "bytes": len(data), "records": len(records), "total": total, "file": str((RAW / raw_name).relative_to(ROOT))})
        print(f"  OK: {len(records)} records; total={total}")
        for record in records: all_records[record["detail_url"]] = record
        if total is not None and offset + page_size >= total: break
        if not records: break
        time.sleep(float(CONFIG["crawler"].get("delay_seconds", 1.0)))

    if failed and not all_records:
        if (OUT / "contracts.json").exists():
            print("Keeping previous successful contracts.json after unavailable/invalid source."); return
        raise RuntimeError("Registr smluv did not return a valid result table; no dataset was imported.")

    payload = {"schema_version": 2, "retrieved_at": datetime.now(timezone.utc).isoformat(), "source": "Registr smluv", "source_url": BASE, "publisher_ico": ICO, "records": list(all_records.values()), "pages": pages, "status": "partial" if failed else "ok"}
    (OUT / "contracts.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "manifest.json").write_text(json.dumps({"retrieved_at": payload["retrieved_at"], "publisher_ico": ICO, "record_count": len(all_records), "pages": pages, "status": payload["status"]}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for old in SOURCE_OUT.glob("*.json"): old.unlink()
    for i, record in enumerate(all_records.values(), 1):
        (SOURCE_OUT / f"contract_{i:06d}.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(all_records)} unique contract records and normalized source records.")


if __name__ == "__main__": main()
