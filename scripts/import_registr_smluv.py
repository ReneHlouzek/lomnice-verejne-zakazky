#!/usr/bin/env python3
"""Import public contract metadata for Lomnice from the official Contract Register.

The register exposes an official machine-readable monthly open-data archive, but
this importer starts with the public search endpoint because it lets us restrict
the acquisition to the city's IČO and avoid downloading the complete national dump.
It stores raw search pages and a normalized JSON dataset for later reconciliation
with VVZ and Vhodné uveřejnění.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
RS = CONFIG["registr_smluv"]
BASE = RS["search_url"]
ICO = RS["publisher_ico"]
OUT = ROOT / "data" / "registr_smluv"
RAW = OUT / "raw"


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
        "subject_idnum": ICO,
        "do": "searchResultList-setOffset",
        "searchResultList-offset": str(offset),
        "search_type": "0",
    }
    return f"{BASE}?{urlencode(params)}"


def parse_page(html: bytes) -> tuple[list[dict], int | None]:
    soup = BeautifulSoup(html, "html.parser")
    records: list[dict] = []

    # The result table has a Detail link for each contract.  We deliberately
    # preserve the visible columns instead of depending on internal CSS classes.
    for row in soup.find_all("tr"):
        cells = row.find_all(["td", "th"])
        if len(cells) < 5:
            continue
        texts = [clean(c.get_text(" ", strip=True)) for c in cells]
        links = [a.get("href") for a in row.find_all("a", href=True)]
        detail = next((detail_url(h) for h in links if "detail" in h.lower() or "smlouva" in h.lower()), None)
        if not detail:
            continue
        records.append({
            "publisher": texts[0],
            "subject": texts[1],
            "last_version": texts[2] if len(texts) > 2 else None,
            "published": texts[3] if len(texts) > 3 else None,
            "value": texts[4] if len(texts) > 4 else None,
            "counterparty": texts[5] if len(texts) > 5 else None,
            "detail_url": detail,
        })

    total = None
    text = soup.get_text(" ", strip=True)
    match = re.search(r"Počet nalezn[ýy]ch záznamů\s+(\d+)", text, re.I)
    if match:
        total = int(match.group(1))
    return records, total


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (compatible; Lomnice-Verejne-Zakazky/0.6; +public-data-archive)",
        "Accept": "text/html,application/xhtml+xml",
    })

    all_records: dict[str, dict] = {}
    pages: list[dict] = []
    page_size = int(RS.get("page_size", 100))
    max_pages = int(RS.get("max_pages", 20))

    for page_no in range(max_pages):
        offset = page_no * page_size
        url = build_url(offset)
        print(f"Registr smluv: {url}")
        try:
            response = session.get(url, timeout=45)
            response.raise_for_status()
        except requests.RequestException as exc:
            print(f"  FAILED: {exc}")
            break

        data = response.content
        raw_name = f"page_{page_no:04d}.html"
        (RAW / raw_name).write_bytes(data)
        records, total = parse_page(data)
        pages.append({
            "page": page_no,
            "offset": offset,
            "url": url,
            "status": "ok",
            "sha256": sha256(data),
            "bytes": len(data),
            "records": len(records),
            "total": total,
            "file": str((RAW / raw_name).relative_to(ROOT)),
        })
        print(f"  OK: {len(records)} records; total={total}")

        for record in records:
            key = record["detail_url"]
            all_records[key] = record

        if total is not None and offset + page_size >= total:
            break
        if not records:
            break
        time.sleep(float(CONFIG["crawler"].get("delay_seconds", 1.0)))

    payload = {
        "schema_version": 1,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "source": "Registr smluv",
        "source_url": BASE,
        "publisher_ico": ICO,
        "records": list(all_records.values()),
        "pages": pages,
    }
    (OUT / "contracts.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (OUT / "manifest.json").write_text(
        json.dumps({
            "retrieved_at": payload["retrieved_at"],
            "publisher_ico": ICO,
            "record_count": len(all_records),
            "pages": pages,
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Wrote {len(all_records)} unique contract records.")


if __name__ == "__main__":
    main()
