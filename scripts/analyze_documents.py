#!/usr/bin/env python3
"""Extract neutral, factual signals from retained PDF text from all supported sources."""
from __future__ import annotations
import json,re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MANIFESTS=[
    ("registr-smluv", ROOT/"data/documents/registr-smluv/manifest.json"),
    ("vhodne-uverejneni", ROOT/"data/documents/manifest.json"),
]
OUT=ROOT/"data/documents/analysis.json"

MONEY=re.compile(r"(?<!\d)(\d{1,3}(?:[ .]\d{3})*(?:,\d{1,2})?)\s*Kč",re.I)
DATE=re.compile(r"\b(?:\d{1,2}\.\s*\d{1,2}\.\s*\d{4}|\d{4}-\d{2}-\d{2})\b")
KEYWORDS={
 "contract":["smlouva o dílo","smlouva","kupní smlouva"],
 "addendum":["dodatek ke smlouvě","dodatek č.","dodatek c."],
 "budget":["rozpočet","položkový rozpočet","soupis prací"],
 "change_sheet":["změnový list","zmenový list","vícepráce","méněpráce","meneprace"],
 "grant":["účelová dotace","individuální dotace","dotace z rozpočtu"],
 "tender":["veřejná zakázka","zadávací řízení","nabídka","uchazeč"],
 "deadline":["termín zahájení","termín ukončení","doba realizace","lhůta"],
}

def classify(name,text):
    s=(name+"\n"+text[:12000]).lower()
    scores={k:sum(1 for x in words if x in s) for k,words in KEYWORDS.items()}
    return [k for k,v in scores.items() if v>0], scores

def snippets(text):
    low=text.lower()
    needles=["cena","celková částka","rozpočet","dodatek","změnový list","vícepráce","méněpráce","dotace","termín ukončení"]
    out=[]
    for n in needles:
        p=low.find(n)
        if p>=0:
            frag=" ".join(text[max(0,p-90):p+260].split())
            if frag and frag not in out: out.append(frag)
    return out[:8]

def main():
    docs=[]
    seen=set()
    for source,manifest in MANIFESTS:
        if not manifest.exists(): continue
        obj=json.loads(manifest.read_text(encoding="utf-8"))
        for rec in obj.get("records",[]):
            for d in rec.get("documents",[]):
                if not d.get("text_file"): continue
                p=ROOT/d["text_file"]
                if not p.exists(): continue
                key=d.get("sha256") or d["text_file"]
                if key in seen: continue
                seen.add(key)
                text=p.read_text(encoding="utf-8",errors="replace")
                cats,scores=classify(d.get("name") or d.get("label") or "",text)
                amounts=[]
                for m in MONEY.finditer(text):
                    v=m.group(1).replace(" ","").replace(".","").replace(",",".")
                    try: amounts.append(float(v))
                    except ValueError: pass
                docs.append({
                    "source":source,
                    "source_id":rec.get("source_id"),
                    "source_url":rec.get("page_url"),
                    "title":rec.get("title"),
                    "document_name":d.get("name") or d.get("label"),
                    "text_file":d["text_file"],
                    "text_chars":len(text),
                    "document_types":cats,
                    "signals":scores,
                    "amounts_czk":sorted(set(amounts))[:30],
                    "dates":sorted(set(DATE.findall(text)))[:40],
                    "snippets":snippets(text),
                })
    OUT.write_text(json.dumps({
        "version":2,"documents_analyzed":len(docs),
        "method":"Pravidlová extrakce z textu PDF; nejde o právní ani ekonomické hodnocení.",
        "documents":docs
    },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Document analysis: analyzed={len(docs)}")

if __name__=="__main__": main()
