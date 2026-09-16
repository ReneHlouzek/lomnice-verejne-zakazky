"""Resolve procurement records from multiple official sources into unified projects.

Input: JSON/JSONL records in data/sources/<source>/. Each record should contain
at least a title plus any available identifiers, buyer/supplier IČO, dates and price.
Output: data/projects/*.json and data/link_candidates.json.

The resolver is deliberately conservative: title-only matches are never merged.
"""
from __future__ import annotations

import json, re, unicodedata
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "data" / "sources"
OUT = ROOT / "data" / "projects"
BUYER_ICO = "00275905"


def norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def ico(v):
    return re.sub(r"\D", "", str(v or ""))


def price(v):
    if v in (None, ""): return None
    try: return float(str(v).replace(" ", "").replace("Kc", "").replace("CZK", "").replace(",", "."))
    except ValueError: return None


def records():
    if not SOURCES.exists(): return []
    out=[]
    for p in SOURCES.rglob("*.json"):
        if p.name == "README.json": continue
        try: obj=json.loads(p.read_text(encoding="utf-8"))
        except Exception: continue
        rows=obj if isinstance(obj,list) else obj.get("records", [obj])
        for r in rows:
            if isinstance(r,dict):
                r=dict(r); r["_source_file"]=str(p.relative_to(ROOT)); out.append(r)
    for p in SOURCES.rglob("*.jsonl"):
        for line in p.read_text(encoding="utf-8").splitlines():
            try:
                r=json.loads(line); r["_source_file"]=str(p.relative_to(ROOT)); out.append(r)
            except Exception: pass
    return [r for r in out if ico(r.get("buyer_ico") or r.get("ico_zadavatele")) in ("", BUYER_ICO)]


def key_ids(r):
    return {str(r.get(k)).strip() for k in ("vvz_id","vvz_identifier","profile_id","procurement_id","contract_id","contract_number") if r.get(k)}


def score(a,b):
    common = key_ids(a) & key_ids(b)
    if common: return 1.0, "exact_identifier", sorted(common)
    ai,bi=ico(a.get("supplier_ico") or a.get("ico_dodavatele")),ico(b.get("supplier_ico") or b.get("ico_dodavatele"))
    at,bt=norm(a.get("title") or a.get("nazev") or a.get("name")),norm(b.get("title") or b.get("nazev") or b.get("name"))
    sim=SequenceMatcher(None,at,bt).ratio() if at and bt else 0
    ap,bp=price(a.get("price") or a.get("contract_price")),price(b.get("price") or b.get("contract_price"))
    same_supplier=bool(ai and bi and ai==bi)
    near_price=bool(ap and bp and (abs(ap-bp)/max(ap,bp) <= .03))
    if same_supplier and sim >= .72 and (near_price or not ap or not bp): return .9,"supplier_title",[ai]
    if sim >= .86 and near_price: return .82,"title_price",[]
    if same_supplier and sim >= .60: return .65,"candidate_supplier_title",[ai]
    return 0,"none",[]


def main():
    rows=records(); groups=[]; candidates=[]
    for r in rows:
        best=None
        for i,g in enumerate(groups):
            s,reason,evidence=score(r,g[0])
            if s and (best is None or s>best[0]): best=(s,reason,evidence,i)
        if best and best[0] >= .82:
            groups[best[3]].append(r)
        else: groups.append([r])
    OUT.mkdir(parents=True,exist_ok=True)
    for old in OUT.glob("*.json"): old.unlink()
    for i,g in enumerate(groups,1):
        base=g[0]; title=base.get("title") or base.get("nazev") or base.get("name") or f"Projekt {i}"
        pid="p-"+re.sub(r"[^a-z0-9]+","-",norm(title))[:70].strip("-")+f"-{i:04d}"
        sources=[]
        for r in g:
            sources.append({"source_file":r.get("_source_file"),"source_id":r.get("source_id") or r.get("vvz_id") or r.get("contract_id"),"record":r})
        (OUT/f"{pid}.json").write_text(json.dumps({"id":pid,"title":title,"buyer_ico":BUYER_ICO,"sources":sources},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    # Cross-source pairs not automatically merged are retained for review.
    for i,a in enumerate(rows):
        for b in rows[i+1:]:
            if a.get("_source_file")==b.get("_source_file"): continue
            s,reason,evidence=score(a,b)
            if .60 <= s < .82:
                candidates.append({"score":s,"reason":reason,"evidence":evidence,"a":a,"b":b})
    (ROOT/"data"/"link_candidates.json").write_text(json.dumps(candidates,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Resolved {len(rows)} source records into {len(groups)} projects; {len(candidates)} candidates for review.")

if __name__ == "__main__": main()
