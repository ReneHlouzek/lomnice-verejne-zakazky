#!/usr/bin/env python3
"""Import rich procurement metadata from the official PVU XML export."""
from __future__ import annotations
import json,re
from pathlib import Path
from xml.etree import ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]; XML_DIR=ROOT/"data/xml"; OUT=ROOT/"data/inbox/vu_xml_enrichment.json"
def tag(e): return e.tag.rsplit("}",1)[-1]
def txt(e,name):
    for c in e.iter():
        if tag(c)==name and (c.text or "").strip(): return (c.text or "").strip()
    return None
def alltxt(e,name): return [(c.text or "").strip() for c in e.iter() if tag(c)==name and (c.text or "").strip()]
def num(v):
    try:return float(v)
    except:return None
rows={}
for path in sorted(XML_DIR.glob("*.xml")):
    try: root=ET.parse(path).getroot()
    except Exception: continue
    for z in root.iter():
        if tag(z)!="zakazka": continue
        sid,title=txt(z,"id_objektu"),txt(z,"nazev_vz")
        if not sid or not title: continue
        parts=[x for x in z.iter() if tag(x)=="cast_zakazky"]; p=parts[0] if parts else z
        participants=[]
        for u in z.iter():
            if tag(u)!="ucastnik": continue
            sub=next((x for x in u if tag(x)=="subjekt"),None)
            participants.append({"supplier_ico":txt(sub,"ico") if sub is not None else None,"supplier_name":txt(sub,"nazev_subjektu") if sub is not None else None,"bid_price":num(txt(u,"nabidkova_cena_s_dph"))})
        selected=[]
        for v in z.iter():
            if tag(v)!="vybrany_dodavatel": continue
            sub=next((x for x in v if tag(x)=="subjekt"),None)
            selected.append({"supplier_ico":txt(sub,"ico") if sub is not None else None,"supplier_name":txt(sub,"nazev_subjektu") if sub is not None else None,"price":num(txt(v,"smluvni_cena_s_DPH"))})
        docs=[]
        for d in z.iter():
            if tag(d)=="dokument" and txt(d,"url"): docs.append({"url":txt(d,"url"),"label":txt(d,"jiny_dokument_nazev") or txt(d,"typ_dokumentu")})
        sel=selected[0] if selected else {}
        rows[sid]={"source_id":sid,"procurement_id":sid,"title":title,"date":txt(z,"datum_uverejneni"),"type":txt(z,"druh_vz"),"procurement_type":txt(z,"druh_vz"),"procurement_regime":txt(z,"rezim_vz"),"procurement_procedure":txt(p,"druh_zadavaciho_postupu"),"status":txt(p,"stav_zadavaciho_postupu"),"description":txt(z,"predmet_vz"),"cpv":alltxt(z,"hlavni_cpv"),"offer_deadline":(alltxt(z,"datum_konce_lhuty") or [None])[-1],"participant_count":len(participants),"bid_count":sum(1 for x in participants if x.get("bid_price") is not None),"supplier_ico":sel.get("supplier_ico"),"supplier_name":sel.get("supplier_name"),"price_vat_included":sel.get("price"),"price":sel.get("price"),"outcome":"vybraný dodavatel" if selected else None,"document_count":len(docs),"xml_documents":docs,"xml_file":str(path.relative_to(ROOT)),"verified_web":True,"verification_level":"official_xml","verification_source":"PVU XMLdataVZ"}
OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(list(rows.values()),ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); print(f"PVU XML enrichment: {len(rows)} zakázek")
