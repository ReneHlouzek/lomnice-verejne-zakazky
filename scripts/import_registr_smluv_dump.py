#!/usr/bin/env python3
"""Import monthly open-data dumps from the Czech Contract Register.

The script is intentionally source-oriented: it keeps raw dump metadata and
extracts only records whose publishing party IČO matches the configured city.
It does not attempt to decide whether a contract belongs to a public
procurement project; that linkage is a later normalization step.
"""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
ICO = CONFIG["source"]["ico"]
INBOX = ROOT / "data" / "inbox" / "registr-smluv"
OUT = ROOT / "data" / "registr-smluv"


def text(node: ET.Element | None) -> str | None:
    if node is None or node.text is None:
        return None
    value = node.text.strip()
    return value or None


def find_any(node: ET.Element, names: tuple[str, ...]) -> ET.Element | None:
    wanted = set(names)
    for child in node.iter():
        if child.tag.rsplit("}", 1)[-1] in wanted:
            return child
    return None


def record_matches_ico(record: ET.Element) -> bool:
    for child in record.iter():
        tag = child.tag.rsplit("}", 1)[-1].lower()
        if tag in {"ico", "icoid", "idnum"} and text(child) == ICO:
            return True
    return False


def extract_record(record: ET.Element) -> dict:
    fields = {}
    aliases = {
        "id": ("id", "idSmlouvy", "idVerze"),
        "subject": ("predmet", "predmetSmlouvy"),
        "date_signed": ("datumUzavreni", "datumUverejneni"),
        "date_published": ("datumUverejneni", "prvniUverejneni"),
        "value_without_vat": ("hodnotaBezDph", "hodnotaBezDphVys"),
        "vvz_reference": ("evCisloVZ", "evCisloZakazkyVVZ", "evCisloZakVVZ"),
    }
    for key, names in aliases.items():
        node = find_any(record, names)
        fields[key] = text(node)

    fields["source"] = "registr-smluv"
    fields["publishing_ico"] = ICO
    return fields


def main() -> None:
    files = sorted(INBOX.glob("*.xml"))
    OUT.mkdir(parents=True, exist_ok=True)
    records: list[dict] = []
    processed: list[str] = []

    for path in files:
        try:
            root = ET.parse(path).getroot()
        except (ET.ParseError, OSError) as exc:
            print(f"SKIP {path}: {exc}")
            continue
        count_before = len(records)
        for node in root.iter():
            if node.tag.rsplit("}", 1)[-1].lower() in {"zaznam", "record", "smlouva"} and record_matches_ico(node):
                records.append(extract_record(node))
        processed.append(path.name)
        print(f"{path.name}: +{len(records) - count_before}")

    # De-duplicate on the strongest available identifier while preserving order.
    unique = {}
    for record in records:
        key = record.get("id") or json.dumps(record, ensure_ascii=False, sort_keys=True)
        unique.setdefault(key, record)

    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "publishing_ico": ICO,
        "files": processed,
        "count": len(unique),
        "records": list(unique.values()),
        "notes": [
            "Records are filtered by publishing-party IČO only.",
            "VVZ linkage is retained when present but is not required.",
            "Do not infer procurement-project identity from contract title alone.",
        ],
    }
    (OUT / "contracts.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT / 'contracts.json'}: {len(unique)} records")


if __name__ == "__main__":
    main()
