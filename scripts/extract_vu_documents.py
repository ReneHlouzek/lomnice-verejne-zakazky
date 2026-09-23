#!/usr/bin/env python3
"""Download and text-extract public documents linked from VU contract pages.

The archive stores document metadata and extracted text, not the original binary
PDFs. This keeps the public data repository manageable while preserving the
information needed for later contract/addendum analysis.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "sources" / "vhodne-uverejneni"
OUT = ROOT / "data" / "documents"
MANIFEST = OUT / "manifest.json"
TIMEOUT = 45
MAX_DOC_BYTES = 25 * 1024 * 1024
WORKERS = 6

PDF_RE = re.compile(r"\.pdf(?:$|[?#])", re.I)


def norm_url(url: str) -> str:
    return urljoin("https://www.vhodne-uverejneni.cz/", url.strip())


def is_document_url(url: str) -> bool:
    path = urlparse(url).path.lower()
    return bool(PDF_RE.search(path)) or any(x in path for x in ("/download", "/document", "/attachment"))


def fetch_page(url: str) -> tuple[str, list[dict]]:
    r = requests.get(url, timeout=TIMEOUT, headers={
        "User-Agent": "Lomnice-Verejne-Zakazky/1.0 (public-data-archive)",
        "Accept": "text/html,application/xhtml+xml",
    })
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    docs = []
    for a in soup.find_all("a", href=True):
        href = norm_url(a["href"])
        label = " ".join(a.stripped_strings)
        if is_document_url(href):
            docs.append({"url": href, "label": label})
    # Some portals expose a document URL in data-* attributes instead of href.
    for tag in soup.find_all(True):
        for key, value in tag.attrs.items():
            if not str(key).startswith("data-"):
                continue
            vals = value if isinstance(value, list) else [value]
            for v in vals:
                if isinstance(v, str) and is_document_url(v):
                    docs.append({"url": norm_url(v), "label": tag.get_text(" ", strip=True)})
    unique = {}
    for d in docs:
        unique[d["url"]] = d
    return r.url, list(unique.values())


def extract_pdf(url: str) -> tuple[dict, str | None]:
    r = requests.get(url, timeout=TIMEOUT, headers={
        "User-Agent": "Lomnice-Verejne-Zakazky/1.0 (public-data-archive)",
        "Accept": "application/pdf,*/*",
    }, stream=True)
    r.raise_for_status()
    data = r.content
    if len(data) > MAX_DOC_BYTES:
        raise ValueError(f"document too large: {len(data)} bytes")
    digest = hashlib.sha256(data).hexdigest()
    meta = {
        "url": r.url,
        "sha256": digest,
        "bytes": len(data),
        "content_type": r.headers.get("content-type", ""),
    }
    if not data.startswith(b"%PDF"):
        return meta, None
    tmp = OUT / ".tmp.pdf"
    tmp.write_bytes(data)
    try:
        reader = PdfReader(str(tmp))
        parts = []
        for page in reader.pages:
            try:
                parts.append(page.extract_text() or "")
            except Exception:
                parts.append("")
        return meta, "\n\n".join(parts).strip()
    finally:
        tmp.unlink(missing_ok=True)


def process(record: dict) -> dict:
    source_id = record.get("source_id") or record.get("procurement_id") or hashlib.sha1(
        record.get("source_url", "").encode()
    ).hexdigest()[:12]
    page_url = record.get("source_url")
    result = {
        "source": "vhodne-uverejneni",
        "source_id": source_id,
        "page_url": page_url,
        "title": record.get("title"),
        "document_count_declared": record.get("document_count"),
        "documents": [],
        "status": "ok",
    }
    if not page_url:
        result["status"] = "missing_page_url"
        return result
    try:
        final_url, docs = fetch_page(page_url)
        result["page_url"] = final_url
    except Exception as exc:
        result["status"] = "page_error"
        result["error"] = str(exc)
        return result

    for i, doc in enumerate(docs, 1):
        item = {"index": i, "label": doc["label"], "url": doc["url"]}
        try:
            meta, text = extract_pdf(doc["url"])
            item.update(meta)
            item["text_available"] = bool(text)
            item["text_chars"] = len(text or "")
            if text:
                item["text_file"] = f"data/documents/{source_id}/{i:03d}.txt"
                outdir = OUT / str(source_id)
                outdir.mkdir(parents=True, exist_ok=True)
                (outdir / f"{i:03d}.txt").write_text(text, encoding="utf-8")
        except Exception as exc:
            item["status"] = "download_error"
            item["error"] = str(exc)
        result["documents"].append(item)
    return result


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    records = []
    seen = set()
    for path in sorted(SRC.glob("*.json")):
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        url = obj.get("source_url")
        if not url or url in seen:
            continue
        seen.add(url)
        if obj.get("verified_web") or obj.get("document_count"):
            records.append(obj)

    results = []
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {pool.submit(process, r): r for r in records}
        for fut in as_completed(futures):
            try:
                results.append(fut.result())
            except Exception as exc:
                r = futures[fut]
                results.append({
                    "source": "vhodne-uverejneni",
                    "source_id": r.get("source_id"),
                    "page_url": r.get("source_url"),
                    "status": "worker_error",
                    "error": str(exc),
                })

    results.sort(key=lambda x: (x.get("source_id") or "", x.get("page_url") or ""))
    declared = sum(int(x.get("document_count_declared") or 0) for x in results)
    discovered = sum(len(x.get("documents", [])) for x in results)
    downloaded = sum(
        1 for x in results for d in x.get("documents", [])
        if d.get("sha256")
    )
    extracted = sum(
        1 for x in results for d in x.get("documents", [])
        if d.get("text_available")
    )
    MANIFEST.write_text(json.dumps({
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "pages_checked": len(results),
        "declared_documents": declared,
        "documents_discovered": discovered,
        "documents_downloaded": downloaded,
        "documents_text_extracted": extracted,
        "records": results,
        "note": "Archives public document metadata and extracted PDF text. Original binaries are not committed.",
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"VU documents: pages={len(results)} declared={declared} discovered={discovered} downloaded={downloaded} text={extracted}")


if __name__ == "__main__":
    main()
