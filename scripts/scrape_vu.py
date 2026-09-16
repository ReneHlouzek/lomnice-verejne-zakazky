"""Resilient crawler for the Lomnice public procurement profile.

The portal has a documented profile URL format based either on a profile slug
or on the organization's IČO. The crawler tries both forms so a timeout on one
public endpoint does not immediately stop collection.
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
SOURCE = CONFIG["source"]
PROFILE = SOURCE["profile_url"]
PROFILE_BY_ICO = f"https://www.vhodne-uverejneni.cz/profil/{SOURCE['ico']}"
TIMEOUT = max(int(CONFIG["crawler"].get("timeout_seconds", 30)), 60)
RETRIES = max(int(CONFIG["crawler"].get("max_retries", 3)), 3)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch(session: requests.Session, urls: list[str]) -> tuple[requests.Response, str]:
    last_errors: list[str] = []
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; Lomnice-Verejne-Zakazky/0.2; +public-data-archive)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "cs-CZ,cs;q=0.9,en;q=0.7",
        "Connection": "keep-alive",
    }

    for url in urls:
        for attempt in range(RETRIES):
            try:
                response = session.get(url, timeout=(15, TIMEOUT), headers=headers, allow_redirects=True)
                response.raise_for_status()
                return response, url
            except requests.RequestException as exc:
                last_errors.append(f"{url}: {type(exc).__name__}: {exc}")
                if attempt + 1 < RETRIES:
                    time.sleep(min(2 ** attempt, 8))

    details = " | ".join(last_errors[-6:])
    raise RuntimeError(f"Nepodařilo se načíst žádnou variantu profilu. {details}")


def collect_links(html: str, base_url: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    result: list[dict[str, str]] = []
    seen: set[str] = set()
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

    candidates = [PROFILE]
    if PROFILE_BY_ICO not in candidates:
        candidates.append(PROFILE_BY_ICO)

    with requests.Session() as session:
        response, successful_url = fetch(session, candidates)

    raw = response.content
    (out / "profile.html").write_bytes(raw)
    links = collect_links(response.text, successful_url)
    (out / "links.json").write_text(
        json.dumps(
            {
                "source_url": successful_url,
                "configured_profile_url": PROFILE,
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
    print(f"Použitý profil: {successful_url}")
    print(f"Nalezeno odkazů: {len(links)}")


if __name__ == "__main__":
    main()
