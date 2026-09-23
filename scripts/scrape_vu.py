"""Best-effort collector for the official PVU XMLdataVZ export.

The GitHub Actions runner may not be able to reach vhodne-uverejneni.cz.
Therefore acquisition failure is recorded as metadata and does not fail the
pipeline. Future XML snapshots can be placed in data/inbox/ and processed by
the import/build stages without changing this collector.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode

import requests

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
PROFILE = CONFIG["source"]["profile_url"].rstrip("/")
TIMEOUT = min(max(int(CONFIG["crawler"].get("timeout_seconds", 30)), 8), 20)
RETRIES = max(int(CONFIG["crawler"].get("max_retries", 3)), 3)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def xml_url(start: date, end: date) -> str:
    params = urlencode({"od": start.strftime("%d%m%Y"), "do": end.strftime("%d%m%Y")})
    return f"{PROFILE}/XMLdataVZ?{params}"


def windows(start: date, end: date) -> list[tuple[date, date]]:
    result = []
    cursor = start
    while cursor <= end:
        window_end = min(cursor + timedelta(days=365), end)
        result.append((cursor, window_end))
        cursor = window_end + timedelta(days=1)
    return result


def fetch_curl(url: str) -> bytes | None:
    with tempfile.NamedTemporaryFile(prefix="pvu-xml-", suffix=".xml", delete=False) as tmp:
        output = tmp.name
    try:
        cmd = [
            "curl", "--fail", "--silent", "--show-error", "--location",
            "--ipv4", "--retry", "1", "--retry-delay", "1", "--max-time", str(TIMEOUT), "--connect-timeout", "5",
            "-A", "Mozilla/5.0 (compatible; Lomnice-Verejne-Zakazky/0.6)",
            "-o", output, url,
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT + 20)
        if proc.returncode != 0:
            return None
        data = Path(output).read_bytes()
        return data or None
    except (OSError, subprocess.SubprocessError):
        return None
    finally:
        Path(output).unlink(missing_ok=True)


def fetch_requests(session: requests.Session, url: str) -> bytes | None:
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; Lomnice-Verejne-Zakazky/0.6; +public-data-archive)",
        "Accept": "application/xml,text/xml,*/*;q=0.8",
    }
    for attempt in range(min(RETRIES, 2)):
        try:
            response = session.get(url, timeout=(5, TIMEOUT), headers=headers, allow_redirects=True)
            response.raise_for_status()
            return response.content
        except requests.RequestException:
            if attempt + 1 < RETRIES:
                time.sleep(min(2 ** attempt, 8))
    return None


def main() -> None:
    today = date.today()
    start = date(2014, 1, 1)
    out_root = ROOT / "data" / "xml"
    out_root.mkdir(parents=True, exist_ok=True)

    results = []
    with requests.Session() as session:
        for start_date, end_date in windows(start, today):
            url = xml_url(start_date, end_date)
            print(f"XML: {url}")
            data = fetch_curl(url)
            method = "curl-ipv4"
            if data is None:
                data = fetch_requests(session, url)
                method = "requests"
            if data is None:
                results.append({
                    "from": start_date.isoformat(),
                    "to": end_date.isoformat(),
                    "url": url,
                    "status": "unavailable",
                })
                print("  unavailable (pipeline continues)")
                continue

            name = f"{start_date:%Y%m%d}_{end_date:%Y%m%d}.xml"
            path = out_root / name
            path.write_bytes(data)
            results.append({
                "from": start_date.isoformat(),
                "to": end_date.isoformat(),
                "url": url,
                "status": "ok",
                "method": method,
                "sha256": sha256_bytes(data),
                "bytes": len(data),
                "file": str(path.relative_to(ROOT)),
            })
            print(f"  OK {len(data)} bytes via {method}")

    manifest = {
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "profile_url": PROFILE,
        "windows": results,
        "successful_windows": sum(item["status"] == "ok" for item in results),
        "note": "PVU access from GitHub Actions is best-effort. Unavailable windows do not fail the workflow.",
    }
    (out_root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
