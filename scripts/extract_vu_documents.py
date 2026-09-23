#!/usr/bin/env python3
"""Download and text-extract public documents linked from VU contract pages."""
from __future__ import annotations
import hashlib, io, json, re, time
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
TIMEOUT = 15
MAX_DOC_BYTES = 25 * 1024 * 1024
WORKERS = 8
PDF_RE = re.compile(r"\.pdf(?:$|[?#])", re.I)
UA = "Lomnice-Verejne-Zakazky/1.0 (public-data-archive)"

def norm_url(url: str) -> str:
    return urljoin("https://www.vhodne-uverejneni.cz/", url.strip())

def is_document_url(url: str) -> bool:
    path = urlparse(url).path.lower()
    return bool(PDF_RE.search(path)) or any(x in path for x in ("/download", "/document", "/attachment"))

def jina_url(url: str) -> str:
    return "https://r.jina.ai/http://" + url.split("://", 1)[1]

def fetch_page(url: str):
    headers = {"User-Agent": UA, "Accept": "text/html,application/xhtml+xml"}
    try:
        r = requests.get(url, timeout=TIMEOUT, headers=headers)
        r.raise_for_status()
        html, final_url, transport = r.text, r.url, "direct"
    except requests.RequestException:
        try:
            import subprocess
            cp = subprocess.run(
                ["curl", "--fail", "--location", "--http1.1",
                 "--retry", "3", "--retry-delay", "2",
                 "--connect-timeout", "8", "--max-time", "20",
                 "-A", UA, "-H", "Accept: text/html,application/xhtml+xml", url],
                check=True, capture_output=True, text=True,
            )
            html, final_url, transport = cp.stdout, url, "curl"
        except Exception:
            r = requests.get(jina_url(url), timeout=10, headers={"User-Agent": UA})
            r.raise_for_status()
            html, final_url, transport = r.text, url, "jina.ai"
    soup = BeautifulSoup(html, "html.parser")
    docs = []
    for a in soup.find_all("a", href=True):
        href = norm_url(a["href"])
        label = " ".join(a.stripped_strings)
        if is_document_url(href):
            docs.append({"url": href, "label": label})
    # X-EN often exposes document downloads through an orderdocument endpoint
    # without a .pdf suffix. Keep those links as documents as well.
    for a in soup.find_all("a", href=True):
        href = norm_url(a["href"])
        label = " ".join(a.stripped_strings)
        if "xenorders" in href.lower() and "orderdocument" in href.lower():
            docs.append({"url": href, "label": label})
    for tag in soup.find_all(True):
        for key, value in tag.attrs.items():
            if not str(key).startswith("data-"):
                continue
            vals = value if isinstance(value, list) else [value]
            for v in vals:
                if isinstance(v, str) and is_document_url(v):
                    docs.append({"url": norm_url(v), "label": tag.get_text(" ", strip=True)})
    unique = {d["url"]: d for d in docs}
    return final_url, list(unique.values()), transport

def extract_pdf(url: str):
    headers = {"User-Agent": UA, "Accept": "application/pdf,*/*"}
    try:
        r = requests.get(url, timeout=TIMEOUT, headers=headers)
        r.raise_for_status()
        data = r.content
        if len(data) > MAX_DOC_BYTES:
            raise ValueError(f"document too large: {len(data)} bytes")
        meta = {"url": r.url, "sha256": hashlib.sha256(data).hexdigest(),
                "bytes": len(data), "content_type": r.headers.get("content-type", ""),
                "transport": "direct"}
        if not data.startswith(b"%PDF"):
            return meta, None
        reader = PdfReader(io.BytesIO(data))
        parts = []
        for page in reader.pages:
            try:
                parts.append(page.extract_text() or "")
            except Exception:
                parts.append("")
        return meta, "\n\n".join(parts).strip()
    except (requests.RequestException, ValueError):
        try:
            import subprocess
            cp = subprocess.run(
                ["curl", "--fail", "--location", "--http1.1",
                 "--retry", "3", "--retry-delay", "2",
                 "--connect-timeout", "8", "--max-time", "25",
                 "-A", UA, "-H", "Accept: application/pdf,*/*", url],
                check=True, capture_output=True,
            )
            data = cp.stdout
            if len(data) > MAX_DOC_BYTES:
                raise ValueError(f"document too large: {len(data)} bytes")
            meta = {"url": url, "sha256": hashlib.sha256(data).hexdigest(),
                    "bytes": len(data), "content_type": "application/pdf",
                    "transport": "curl"}
            if not data.startswith(b"%PDF"):
                return meta, None
            reader = PdfReader(io.BytesIO(data))
            parts = []
            for page in reader.pages:
                try:
                    parts.append(page.extract_text() or "")
                except Exception:
                    parts.append("")
            return meta, "\n\n".join(parts).strip()
        except Exception:
            pr = requests.get(jina_url(url), timeout=TIMEOUT, headers={"User-Agent": UA})
            pr.raise_for_status()
            text = pr.text.strip()
            return {"url": url, "content_type": "text/markdown; proxy=jina.ai",
                    "transport": "jina.ai"}, text or None

def process(record: dict) -> dict:
    source_id = record.get("source_id") or record.get("procurement_id") or hashlib.sha1(
        record.get("source_url", "").encode()).hexdigest()[:12]
    page_url = record.get("source_url")
    result = {"source": "vhodne-uverejneni", "source_id": source_id,
              "page_url": page_url, "title": record.get("title"),
              "document_count_declared": record.get("document_count"),
              "documents": [], "status": "ok"}
    if not page_url:
        result["status"] = "missing_page_url"
        return result
    try:
        final_url, docs, transport = fetch_page(page_url)
        result["page_url"], result["transport"] = final_url, transport
    except Exception as exc:
        result["status"], result["error"] = "page_error", str(exc)
        return result
    for i, doc in enumerate(docs, 1):
        item = {"index": i, "label": doc["label"], "url": doc["url"]}
        try:
            meta, text = extract_pdf(doc["url"])
            item.update(meta)
            item["text_available"], item["text_chars"] = bool(text), len(text or "")
            if text:
                item["text_file"] = f"data/documents/{source_id}/{i:03d}.txt"
                outdir = OUT / str(source_id)
                outdir.mkdir(parents=True, exist_ok=True)
                (outdir / f"{i:03d}.txt").write_text(text, encoding="utf-8")
        except Exception as exc:
            item["status"], item["error"] = "download_error", str(exc)
        result["documents"].append(item)
    return result

def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    records, seen = [], set()
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
                results.append({"source": "vhodne-uverejneni", "source_id": r.get("source_id"),
                                "page_url": r.get("source_url"), "status": "worker_error",
                                "error": str(exc)})
    results.sort(key=lambda x: (x.get("source_id") or "", x.get("page_url") or ""))
    declared = sum(int(x.get("document_count_declared") or 0) for x in results)
    discovered = sum(len(x.get("documents", [])) for x in results)
    downloaded = sum(1 for x in results for d in x.get("documents", []) if d.get("sha256"))
    extracted = sum(1 for x in results for d in x.get("documents", []) if d.get("text_available"))
    MANIFEST.write_text(json.dumps({
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "pages_checked": len(results), "declared_documents": declared,
        "documents_discovered": discovered, "documents_downloaded": downloaded,
        "documents_text_extracted": extracted, "records": results,
        "note": "Archives public document metadata and extracted PDF text. Original binaries are not committed; inaccessible documents are retained in the manifest as errors."
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"VU documents: pages={len(results)} declared={declared} discovered={discovered} downloaded={downloaded} text={extracted}")

if __name__ == "__main__":
    main()
