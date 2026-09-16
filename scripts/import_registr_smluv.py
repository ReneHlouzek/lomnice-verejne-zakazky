#!/usr/bin/env python3
"""Import metadata from the official Registr smluv monthly XML dumps."""
from __future__ import annotations

import hashlib
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
ICO = CONFIG["registr_smluv"]["publisher_ico"]
OUT = ROOT / "data" / "registr_smluv"
RAW = OUT / "raw_xml"
SOURCE_OUT = ROOT / "data" / "sources" / "registr-smluv"
INDEX_URL = "https://data.smlouvy.gov.cz/index.xml"


def text(el, *names):
    for name in names:
        child = el.find(f".//{{*}}{name}")
        if child is not None and child.text:
            return child.text.strip()
    return None


def ico(value):
    if not value:
        return None
    m = re.search(r"(?<!\d)(\d{8})(?!\d)", value)
    return m.group(1) if m else None


def number(value):
    if not value:
        return None
    s = re.sub(r"[^0-9,.-]", "", value.replace("\xa0", "").replace(" ", ""))
    if not s:
        return None
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    elif "," in s:
        p = s.split(",")
        s = "".join(p) if len(p) > 2 or (len(p) == 2 and len(p[1]) == 3) else ".".join(p)
    return float(s)


def normalize_date(value):
    if not value:
        return None
    value = value.strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
        try:
            return datetime.strptime(value[:26], fmt).date().isoformat()
        except ValueError:
            pass
    return value


def local_name(tag):
    return tag.rsplit("}", 1)[-1].lower()


def children(el, names):
    wanted = {n.lower() for n in names}
    return [c for c in list(el) if local_name(c.tag) in wanted]


def find_party_icos(record):
    values = []
    for el in record.iter():
        n = local_name(el.tag)
        if n in {"ico", "ic", "icopublikujiciho", "icoosoby"} and el.text:
            v = ico(el.text)
            if v:
                values.append(v)
    return list(dict.fromkeys(values))


def parse_record(record):
    # The dump schema has evolved; use local element names and tolerate
    # additional nesting so historical dumps remain importable.
    values = {}
    for el in record.iter():
        n = local_name(el.tag)
        if el.text and n not in values:
            values[n] = el.text.strip()
    parties = find_party_icos(record)
    if ICO not in parties:
        return None
    contract_id = values.get("id") or values.get("idsmlouvy") or values.get("idverze")
    title = values.get("predmet") or values.get("predmetsmlouvy") or values.get("nazev")
    published = values.get("datumzverejneni") or values.get("caszverejneni") or values.get("published")
    signed = values.get("datumuzavreni") or values.get("datumsmlouvy")
    value = values.get("hodnotabezph") or values.get("hodnotabezdp") or values.get("hodnota") or values.get("value")
    detail = values.get("url") or values.get("odkaz") or (f"https://smlouvy.gov.cz/smlouva/{contract_id}" if contract_id else None)
    supplier = next((p for p in parties if p != ICO), None)
    return {
        "source_id": contract_id or detail or f"rs-{hashlib.sha1(ET.tostring(record)).hexdigest()[:16]}",
        "source_url": detail,
        "title": title,
        "buyer_ico": ICO,
        "supplier_ico": supplier,
        "contract_number": values.get("cislosmlouvy") or values.get("evidencnicislo"),
        "date": normalize_date(published or signed),
        "signed_date": normalize_date(signed),
        "price": number(value),
        "publisher": values.get("nazevpublikujiciho") or values.get("publikujici"),
        "subject": title,
        "published": normalize_date(published),
        "value": value,
        "counterparty": supplier,
        "detail_url": detail,
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    SOURCE_OUT.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({"User-Agent": "Lomnice-Verejne-Zakazky/1.0 (+public-data-archive)", "Accept": "application/xml,text/xml,*/*"})

    r = session.get(INDEX_URL, timeout=60)
    r.raise_for_status()
    index = ET.fromstring(r.content)
    dumps = []
    for el in index.iter():
        if local_name(el.tag) != "odkaz" or not el.text:
            continue
        url = el.text.strip()
        if "dump_" in url and url.lower().endswith(".xml"):
            dumps.append(url)
    if not dumps:
        raise RuntimeError("Oficiální index Registru smluv neobsahuje žádný XML dump.")

    # Import all monthly dumps. The official documentation states that dumps
    # are complete monthly metadata snapshots and may be revised retroactively.
    records = {}
    manifests = []
    for url in dict.fromkeys(dumps):
        name = Path(urlparse(url).path).name
        data = session.get(url, timeout=180).content
        if not data:
            raise RuntimeError(f"Prázdný XML dump: {url}")
        (RAW / name).write_bytes(data)
        root = ET.fromstring(data)
        matched = 0
        for el in root.iter():
            if local_name(el.tag) != "zaznam":
                continue
            rec = parse_record(el)
            if rec:
                records[rec["source_id"]] = rec
                matched += 1
        manifests.append({"url": url, "file": str((RAW / name).relative_to(ROOT)), "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data), "matched": matched})

    if not records:
        raise RuntimeError(f"XML dumpy byly staženy, ale žádný záznam neobsahuje IČO {ICO}.")

    payload = {"schema_version": 3, "retrieved_at": datetime.now(timezone.utc).isoformat(), "source": "Registr smluv – otevřená data", "source_url": INDEX_URL, "publisher_ico": ICO, "records": list(records.values()), "dumps": manifests, "status": "ok"}
    (OUT / "contracts.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "manifest.json").write_text(json.dumps({"retrieved_at": payload["retrieved_at"], "publisher_ico": ICO, "record_count": len(records), "dump_count": len(manifests), "status": "ok"}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for old in SOURCE_OUT.glob("*.json"):
        old.unlink()
    for i, rec in enumerate(records.values(), 1):
        (SOURCE_OUT / f"contract_{i:06d}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Imported {len(records)} unique Registr smluv records from {len(manifests)} XML dumps.")


if __name__ == "__main__":
    main()
