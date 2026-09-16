#!/usr/bin/env python3
"""Build a provisional procurement index from the latest Vhodné uveřejnění snapshot.

The first phase deliberately avoids guessing the portal's internal status markup.
It preserves every discovered source link and marks the index as provisional until
we can inspect a real snapshot and implement exact status/detail parsing.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOTS = ROOT / "data" / "snapshots"
INDEX = ROOT / "data" / "index.json"
CONFIG = ROOT / "config.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def latest_snapshot() -> Path | None:
    candidates = [p for p in SNAPSHOTS.iterdir() if p.is_dir()]
    return sorted(candidates)[-1] if candidates else None


def main() -> None:
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    snap = latest_snapshot()
    if snap is None or not (snap / "links.json").exists():
        print("No snapshot found; index not rebuilt.")
        return

    links = json.loads((snap / "links.json").read_text(encoding="utf-8"))
    source_links = links.get("links", [])

    # Keep links unique while preserving source order.
    seen: set[str] = set()
    items = []
    for link in source_links:
        href = link.get("href")
        if not href:
            continue
        absolute = urljoin(cfg["source"]["profile_url"], href)
        if absolute in seen:
            continue
        seen.add(absolute)
        items.append({
            "title": (link.get("text") or "").strip(),
            "url": absolute,
            "classification": "unclassified",
        })

    statuses = cfg["statuses"]
    index = {
        "schema_version": 1,
        "parser_state": "provisional",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": cfg["source"],
        "latest_snapshot": {
            "directory": snap.name,
            "profile_sha256": sha256(snap / "profile.html") if (snap / "profile.html").exists() else None,
        },
        "counts": {key: 0 for key in statuses},
        "statuses": {
            key: {"label": label, "projects": []}
            for key, label in statuses.items()
        },
        "unclassified_links": items,
        "notes": [
            "Status classification is intentionally disabled until the portal HTML structure is verified from a real snapshot.",
            "Do not interpret an unclassified link as a procurement project until its detail page is parsed and normalized.",
        ],
    }

    INDEX.parent.mkdir(parents=True, exist_ok=True)
    INDEX.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {INDEX} with {len(items)} unique source links.")


if __name__ == "__main__":
    main()
