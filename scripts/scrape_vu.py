"""Crawler skeleton for Vhodné uveřejnění.

The first implementation intentionally focuses on resilient source discovery:
- fetch the profile
- detect the four status sections
- collect pagination URLs
- collect tender/detail URLs
- save a raw HTML snapshot for parser tests

Parsing selectors should be extended only after inspecting the live HTML structure.
"""

from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
PROFILE = CONFIG["source"]["profile_url"]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch(session: requests.Session, url: str) -> requests.Response:
    last_error = None
    for attempt in range(CONFIG["crawler"]["max_retries"]):
        try:
            response = session.get(
                url,
                timeout=CONFIG["crawler"]["timeout_seconds"],
                headers={"User-Agent": "Lomnice-Verejne-Zakazky/0.1 (+public-data-archive)"},
            )
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            last_error = exc
            if attempt + 1 < CONFIG["crawler"]["max_retries"]:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"Nepodařilo se načíst {url}: {last_error}")


def collect_links(html: str, base_url: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    result = []
    seen = set()
    for a in soup.find_all("a", href=True):
        href = urljoin(base_url, a["href"])
        if href in seen:
            continue
        seen.add(href)
        text = " ".join(a.stripped_strings)
        result.append({"text": text, "url": href})
    return result


def main() -> None:
    retrieved_at = datetime.now(timezone.utc).isoformat()
    out = ROOT / "data" / "snapshots" / retrieved_at.replace(":", "-")
    out.mkdir(parents=True, exist_ok=True)

    with requests.Session() as session:
        response = fetch(session, PROFILE)

    raw = response.content
    (out / "profile.html").write_bytes(raw)
    links = collect_links(response.text, PROFILE)
    (out / "links.json").write_text(
        json.dumps(
            {
                "source_url": PROFILE,
                "retrieved_at": retrieved_at,
                "sha256": sha256_bytes(raw),
                "links": links,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Snapshot uložen: {out}")
    print(f"Nalezeno odkazů: {len(links)}")


if __name__ == "__main__":
    main()
