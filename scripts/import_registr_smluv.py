#!/usr/bin/env python3
"""Import metadata from the official Registr smluv monthly XML dumps."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
ICO = CONFIG["registr_smluv"]["publisher_ico"]
OUT = ROOT / "data" / "registr_smluv"
RAW = OUT / "raw_xml"
SOURCE_OUT = ROOT / "data" / "sources" / "registr-smluv"
INDEX_URL = "https://data.smlouvy.gov.cz/index.xml"
USER_AGENT = "Lomnice-Verejne-Zakazky/1.0 (+public-data-archive)"


def download(url: str, target: Path, timeout: int) -> None:
    """Download through curl; the public dump server can close Python HTTP connections."""
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".part")
    cmd = [
        "curl", "--fail", "--location", "--http1.1",
        "--retry", "6", "--retry-delay", "5", "--retry-all-errors",
        "--connect-timeout", "30", "--max-time", str(timeout),
        "--user-agent", USER_AGENT, "--output", str(tmp), url,
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or "").strip().splitlines()[-3:]
        raise RuntimeError(f"Stažení selhalo: {url}\n" + "\n".join(detail)) from exc
    if not tmp.exists() or tmp.stat().st_size == 0:
        raise RuntimeError(f"Prázdný download: {url}")
    tmp.replace(target)


def local_name(tag):
    return tag.rsplit("}", 1)[-1].lower()


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


def find_party_icos(record):
    values = []
    for el in record.iter():
        if local_name(el.tag) in {"ico", "ic", "icopublikujiciho", "icoosoby"} and el.text:
            value = ico(el.text)
            if value:
                values.append(value)
    return list(dict.fromkeys(values))


def parse_record(record):
    values = {}
    for el in record.iter():
        name = local_name(el.tag)
        if el.text and name not in values:
            values[name] = el.text.strip()
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


def dump_urls(index_file: Path):
    root = ET.parse(index_file).getroot()
    result = []
    for el in root.iter():
        if local_name(el.tag) == "odkaz" and el.text:
            url = el.text.strip()
            if "dump_" in url and url.lower().endswith(".xml"):
                result.append(url)
    return list(dict.fromkeys(result))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    SOURCE_OUT.mkdir(parents=True, exist_ok=True)

    index_file = OUT / "index.xml"
    download(INDEX_URL, index_file, 120)
    dumps = dump_urls(index_file)
    if not dumps:
        raise RuntimeError("Oficiální index Registru smluv neobsahuje žádný XML dump.")

    records = {}
    manifests = []
    for number_, url in enumerate(dumps, 1):
        name = Path(urlparse(url).path).name
        target = RAW / name
        if not target.exists() or target.stat().st_size == 0:
            print(f"[{number_}/{len(dumps)}] stahuji {name}")
            download(url, target, 900)
        else:
            print(f"[{number_}/{len(dumps)}] používám cache {name}")

        matched = 0
        for _event, el in ET.iterparse(target, events=("end",)):
            if local_name(el.tag) != "zaznam":
                continue
            rec = parse_record(el)
            if rec:
                records[rec["source_id"]] = rec
                matched += 1
            el.clear()

        data_sha = hashlib.sha256(target.read_bytes()).hexdigest()
        manifests.append({
            "url": url,
            "file": str(target.relative_to(ROOT)),
            "sha256": data_sha,
            "bytes": target.stat().st_size,
            "matched": matched,
        })
        print(f"  nalezeno {matched} záznamů pro IČO {ICO}")

    if not records:
        raise RuntimeError(f"XML dumpy byly staženy, ale žádný záznam neobsahuje IČO {ICO}.")

    retrieved = datetime.now(timezone.utc).isoformat()
    payload = {
        "schema_version": 3,
        "retrieved_at": retrieved,
        "source": "Registr smluv – otevřená data",
        "source_url": INDEX_URL,
        "publisher_ico": ICO,
        "records": list(records.values()),
        "dumps": manifests,
        "status": "ok",
    }
    (OUT / "contracts.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "manifest.json").write_text(json.dumps({
        "retrieved_at": retrieved,
        "publisher_ico": ICO,
        "record_count": len(records),
        "dump_count": len(manifests),
        "status": "ok",
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for old in SOURCE_OUT.glob("*.json"):
        old.unlink()
    for i, rec in enumerate(records.values(), 1):
        (SOURCE_OUT / f"contract_{i:06d}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Imported {len(records)} unique Registr smluv records from {len(manifests)} XML dumps.")


if __name__ == "__main__":
    main()
