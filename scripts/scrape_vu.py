"""Crawler for the Lomnice public procurement profile.

Some cloud runners cannot connect to PVU with Python requests. Before giving up,
we try the system curl client with IPv4 forced. This distinguishes a possible
IPv6/routing issue from a genuine upstream block.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
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


def fetch_with_curl(url: str) -> tuple[bytes, str] | None:
    with tempfile.NamedTemporaryFile(prefix="pvu-", suffix=".html", delete=False) as tmp:
        output = tmp.name
    try:
        cmd = [
            "curl", "--fail", "--silent", "--show-error", "--location",
            "--ipv4", "--max-time", str(TIMEOUT), "--connect-timeout", "15",
            "-A", "Mozilla/5.0 (compatible; Lomnice-Verejne-Zakazky/0.4)",
            "-o", output, "-w", "%{url_effective}", url,
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT + 20)
        if proc.returncode != 0:
            return None
        data = Path(output).read_bytes()
        return (data, proc.stdout.strip() or url) if data else None
    except (OSError, subprocess.SubprocessError):
        return None
    finally:
        Path(output).unlink(missing_ok=True)


def fetch(session: requests.Session, urls: list[str]) -> tuple[bytes, str, str]:
    errors: list[str] = []
    for url in urls:
        result = fetch_with_curl(url)
        if result:
            data, final_url = result
            return data, final_url, "curl-ipv4"
        errors.append(f"curl-ipv4 {url}: failed")

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; Lomnice-Verejne-Zakazky/0.4; +public-data-archive)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "cs-CZ,cs;q=0.9,en;q=0.7",
    }
    for url in urls:
        for attempt in range(RETRIES):
            try:
                response = session.get(url, timeout=(10, TIMEOUT), headers=headers, allow_redirects=True)
                response.raise_for_status()
                return response.content, response.url, "requests"
            except requests.RequestException as exc:
                errors.append(f"requests {url}: {type(exc).__name__}: {exc}")
                if attempt + 1 < RETRIES:
                    time.sleep(min(2 ** attempt, 8))
    raise RuntimeError("Nepodařilo se načíst žádnou variantu profilu. " + " | ".join(errors[-12:]))


def collect_links(html: str, base_url: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    result: list[dict[str, str]] = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = urljoin(base_url, a["href"])
        if href in seen:
            continue
        seen.add(href)
        result.append({"text": " ".join(a.stripped_strings), "url": href})
    return result


def main() -> None:
    retrieved_at = datetime.now(timezone.utc).isoformat()
    out = ROOT / "data" / "snapshots" / retrieved_at.replace(":", "-")
    out.mkdir(parents=True, exist_ok=True)
    candidates = candidate_urls()
    print("Testované varianty profilu:")
    for url in candidates:
        print(f" - {url}")
    print("Nejprve zkouším curl s vynuceným IPv4...")

    with requests.Session() as session:
        raw, successful_url, method = fetch(session, candidates)

    (out / "profile.html").write_bytes(raw)
    html = raw.decode("utf-8", errors="replace")
    links = collect_links(html, successful_url)
    (out / "links.json").write_text(
        json.dumps({
            "source_url": successful_url,
            "configured_profile_url": PROFILE,
            "retrieved_at": retrieved_at,
            "sha256": sha256_bytes(raw),
            "method": method,
            "links": links,
        }, ensure_ascii=False, indent=2), encoding="utf-8",
    )
    print(f"Snapshot uložen: {out}")
    print(f"Použitý profil: {successful_url}")
    print(f"Metoda: {method}")
    print(f"Nalezeno odkazů: {len(links)}")


if __name__ == "__main__":
    main()
