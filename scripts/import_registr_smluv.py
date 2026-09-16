#!/usr/bin/env python3
"""Import contracts for the city from the official Contract Register monthly dumps.

Processes each monthly dump immediately after download. This keeps the working
set small and, importantly, preserves already extracted records when a later
large dump is interrupted.
"""
from __future__ import annotations

import json
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config.json"
OUT_DIR = ROOT / "data" / "registr_smluv"
RAW_DIR = OUT_DIR / "raw_xml"
SOURCE_DIR = ROOT / "data" / "sources" / "registr-smluv"
CONTRACTS = OUT_DIR / "contracts.json"
MANIFEST = OUT_DIR / "manifest.json"
NS_RE = re.compile(r"\{[^}]+\}")


def text(el: ET.Element | None) -> str:
    return "" if el is None else " ".join("".join(el.itertext()).split())


def local(tag: str) -> str:
    return NS_RE.sub("", tag)


def children_map(el: ET.Element) -> dict[str, list[ET.Element]]:
    out: dict[str, list[ET.Element]] = {}
    for child in el.iter():
        if child is el:
            continue
        out.setdefault(local(child.tag), []).append(child)
    return out


def first_value(m: dict[str, list[ET.Element]], *names: str) -> str:
    for name in names:
        for el in m.get(name, []):
            value = text(el)
            if value:
                return value
    return ""


def normalize_ico(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def curl_download(url: str, target: Path, timeout: int) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix="dump_", suffix=".part", dir=target.parent)
    Path(name).unlink(missing_ok=True)
    tmp = Path(name)
    try:
        cmd = [
            "curl", "--fail", "--location", "--http1.1",
            "--retry", "5", "--retry-delay", "4", "--retry-all-errors",
            "--connect-timeout", "30", "--max-time", str(timeout),
            "-A", "Lomnice-verejne-zakazky/1.0", "-o", str(tmp), url,
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        tmp.replace(target)
    finally:
        tmp.unlink(missing_ok=True)
        try:
            import os
            os.close(fd)
        except OSError:
            pass


def load_config() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def download_index(timeout: int) -> ET.Element:
    target = OUT_DIR / "index.xml"
    curl_download("https://data.smlouvy.gov.cz/index.xml", target, timeout)
    return ET.parse(target).getroot()


def parse_dumps(root: ET.Element) -> list[dict]:
    dumps = []
    for el in root.iter():
        if local(el.tag) != "odkaz":
            continue
        url = text(el)
        if "dump_" not in url or not url.lower().endswith(".xml"):
            continue
        values = {local(child.tag): text(child) for child in el}
        m = re.search(r"dump_(\d{4})_(\d{2})\.xml", url)
        if not m:
            continue
        dumps.append({
            "url": url,
            "year": int(values.get("rok") or m.group(1)),
            "month": int(values.get("mesic") or m.group(2)),
            "hash": values.get("hashDumpu", ""),
            "size": int(values.get("velikostDumpu") or 0),
            "generated": values.get("casGenerovani", ""),
            "completed": values.get("dokoncenyMesic", ""),
        })
    unique = {d["url"]: d for d in dumps}
    return sorted(unique.values(), key=lambda d: (d["year"], d["month"]))


def extract_records(path: Path, ico: str) -> Iterable[dict]:
    for _, elem in ET.iterparse(path, events=("end",)):
        if local(elem.tag) != "zaznam":
            continue
        m = children_map(elem)
        all_icos = {normalize_ico(text(x)) for key in ("ico", "ic", "icopublikujiciho", "icoosoby") for x in m.get(key, [])}
        if ico not in all_icos:
            elem.clear()
            continue

        title = first_value(m, "predmetSmlouvy", "predmet", "nazevSmlouvy", "nazev")
        contract_id = first_value(m, "idSmlouvy", "id")
        version_id = first_value(m, "idVerze", "versionId")
        publisher = first_value(m, "nazevPublikujiciho", "publikujici")
        signed = first_value(m, "datumUzavreni", "datumPodpisu")
        published = first_value(m, "datumUverejneni", "datumPublikace", "casUverejneni")
        number = first_value(m, "cisloSmlouvy", "cisloJednaci", "evidencniCisloZakazky")
        price = first_value(m, "hodnotaBezDph", "hodnota", "cenaBezDph")
        supplier = ""
        counterparty = ""
        for party_tag in ("smluvniStrana", "strana", "subjekt"):
            for party in m.get(party_tag, []):
                pm = children_map(party)
                picos = [normalize_ico(text(x)) for x in pm.get("ico", []) + pm.get("ic", [])]
                pname = first_value(pm, "nazev", "jmeno", "obchodniJmeno")
                if not picos and not pname:
                    continue
                if ico in picos:
                    continue
                if not supplier:
                    supplier = picos[0] if picos else ""
                    counterparty = pname

        detail = "https://smlouvy.gov.cz/smlouva/" + contract_id if contract_id else ""
        yield {
            "source": "registr-smluv",
            "source_id": contract_id or version_id,
            "version_id": version_id,
            "source_url": detail,
            "title": title,
            "buyer_ico": ico,
            "supplier_ico": supplier,
            "contract_number": number,
            "date": signed or published,
            "signed_date": signed,
            "published": published,
            "price": price,
            "value": price,
            "publisher": publisher,
            "subject": title,
            "counterparty": counterparty,
            "detail_url": detail,
        }
        elem.clear()


def save_outputs(records_by_id: dict[str, dict], processed: dict[str, str], cfg: dict, dumps_count: int, downloaded: int) -> None:
    records = list(records_by_id.values())
    records.sort(key=lambda x: (x.get("published") or x.get("date") or "", x.get("source_id") or ""))
    CONTRACTS.write_text(json.dumps({"records": records, "total": len(records)}, ensure_ascii=False, indent=2), encoding="utf-8")
    for old in SOURCE_DIR.glob("contract_*.json"):
        old.unlink()
    for n, record in enumerate(records, 1):
        (SOURCE_DIR / f"contract_{n:06d}.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    settings = cfg.get("registr_smluv", {})
    MANIFEST.write_text(json.dumps({
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "publisher_ico": normalize_ico(settings.get("publisher_ico", "00275905")),
        "history_from": settings.get("history_from", "2016-07"),
        "recent_months": int(settings.get("recent_months", 2)),
        "dump_count_considered": dumps_count,
        "downloaded_this_run": downloaded,
        "records_total": len(records),
        "processed_dumps": processed,
    }, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    cfg = load_config()
    settings = cfg.get("registr_smluv", {})
    ico = normalize_ico(settings.get("publisher_ico", "00275905"))
    timeout = int(cfg.get("crawler", {}).get("timeout_seconds", 30))
    max_dumps = int(settings.get("max_dumps", settings.get("max_pages", 0)))
    history_from = settings.get("history_from", "2016-07")
    recent_months = int(settings.get("recent_months", 2))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)

    index = download_index(timeout)
    dumps = parse_dumps(index)
    if not dumps:
        raise RuntimeError("Registr smluv: index.xml neobsahuje žádné měsíční dumpy")

    min_year, min_month = map(int, history_from.split("-"))
    dumps = [d for d in dumps if (d["year"], d["month"]) >= (min_year, min_month)]
    if max_dumps > 0:
        dumps = dumps[-max_dumps:]

    old_manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    processed = old_manifest.get("processed_dumps", {})
    records_by_id: dict[str, dict] = {}
    old_contracts = json.loads(CONTRACTS.read_text(encoding="utf-8")) if CONTRACTS.exists() else {}
    for r in old_contracts.get("records", []):
        key = str(r.get("source_id") or r.get("version_id") or "")
        if key:
            records_by_id[key] = r

    refresh_urls = {d["url"] for d in dumps[-recent_months:]}
    processed_now = dict(processed)
    downloaded = 0
    matched = 0

    for i, d in enumerate(dumps, 1):
        key = d["url"]
        unchanged = processed.get(key) == d["hash"] and d["hash"]
        if unchanged and key not in refresh_urls:
            print(f"[{i}/{len(dumps)}] {d['year']}-{d['month']:02d}: beze změny", flush=True)
            continue

        target = RAW_DIR / f"dump_{d['year']:04d}_{d['month']:02d}.xml"
        try:
            curl_download(key, target, 900)
            downloaded += 1
            found_this_dump = 0
            for record in extract_records(target, ico):
                rid = str(record.get("source_id") or record.get("version_id") or "")
                if rid:
                    records_by_id[rid] = record
                    found_this_dump += 1
            matched += found_this_dump
            processed_now[key] = d["hash"]
            save_outputs(records_by_id, processed_now, cfg, len(dumps), downloaded)
            print(f"[{i}/{len(dumps)}] {d['year']}-{d['month']:02d}: nalezeno={found_this_dump}, celkem={len(records_by_id)}", flush=True)
        finally:
            target.unlink(missing_ok=True)

    save_outputs(records_by_id, processed_now, cfg, len(dumps), downloaded)
    print(f"Registr smluv hotov: {len(records_by_id)} záznamů, {downloaded} dumpů staženo.")


if __name__ == "__main__":
    main()
