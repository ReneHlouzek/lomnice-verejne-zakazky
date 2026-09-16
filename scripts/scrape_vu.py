"""Resilient crawler for the Lomnice public procurement profile.

The PVU host can be unreachable from some cloud runners. We therefore try
multiple canonical host/scheme variants before failing. The crawler keeps the
raw response and a link manifest so later parsing can be improved without
re-downloading the source.
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
SLUG = PROFILE.rstrip("/").split("/profil/", 1)[-1]
ICO = SOURCE["ico"]
TIMEOUT = max(int(CONFIG["crawler"].get("timeout_seconds", 30)), 60)
RETRIES = max(int(CONFIG["crawler"].get("max_retries", 3)), 3)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def candidate_urls() -> list[str]:
    """Return canonical variants, de-duplicated and ordered by preference."""
    urls = [
        PROFILE,
        f"https://www.vhodne-uverejneni.cz/profil/{ICO}",
        f"https://vhodne-uverejneni.cz/profil/{SLUG}",
        f"https://vhodne-uverejneni.cz/profil/{ICO}",
        f"http://www.vhodne-uverejneni.cz/profil/{SLUG}",
        f"http://www.vhodne-uverejneni.cz/profil/{ICO}",
        f"http://vhodne-uverejneni.cz/profil/{SLUG}",
        f"http://vhodne-uverejneni.cz/profil/{ICO}",
    ]
    return list(dict.fromkeys(urls))


def fetch(session: requests.Session, urls: list[str]) -> tuple[requests.Response, str]:
    last_errors: list[str] = []
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; Lomnice-Verejne-Zakazky/0.3; +public-data-archive)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "cs-CZ,cs;q=0.9,en;q=0.7",
        "Connection": "keep-alive",
    }

    for url in urls:
        for attempt in range(RETRIES):
            try:
                response = session.get(
                    url,
                    timeout=(10, TIMEOUT),
                    headers=headers,
                    allow_redirects=True,
                )
                response.raise_for_status()
                return response, url
            except requests.RequestException as exc:
                last_errors.append(f"{url}: {type(exc).__name__}: {exc}")
                if attempt + 1 < RETRIES:
                    time.sleep(min(2 ** attempt, 8))

    details = " | ".join(last_errors[-10:])
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

    candidates = candidate_urls()
    print("Testované varianty profilu:")
    for url in candidates:
        print(f" - {url}")

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
