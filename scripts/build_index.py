#!/usr/bin/env python3
"""Build the public index from resolved projects and source manifests."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PROJECTS=ROOT/"data"/"projects"
INDEX=ROOT/"data"/"index.json"
CONFIG=json.loads((ROOT/"config.json").read_text(encoding="utf-8"))

def main():
    projects=[]
    if PROJECTS.exists():
        for p in sorted(PROJECTS.glob("*.json")):
            try: projects.append(json.loads(p.read_text(encoding="utf-8")))
            except Exception: continue
    statuses=CONFIG["statuses"]
    buckets={k:[] for k in statuses}
    types={"procurement":[],"procurement_with_changes":[],"contract_with_changes":[],"contract":[],"other":[],"unclassified":[]}
    for p in projects:
        status=p.get("status") or "unclassified"
        if status in buckets: buckets[status].append(p["id"])
        typ=p.get("project_type") or p.get("canonical",{}).get("project_type") or "other"
        types.setdefault(typ,[]).append(p["id"])
    index={
      "schema_version":3,
      "parser_state":"resolved" if projects else "awaiting-source-data",
      "generated_at":datetime.now(timezone.utc).isoformat(),
      "source":CONFIG["source"],
      "counts":{k:len(v) for k,v in buckets.items()},
      "project_type_counts":{k:len(v) for k,v in types.items()},
      "total_projects":len(projects),
      "statuses":{k:{"label":v,"projects":buckets[k]} for k,v in statuses.items()},
      "project_types":{
        "procurement":{"label":"Veřejná zakázka / výběr / smlouva","projects":types.get("procurement",[])},
        "procurement_with_changes":{"label":"Zakázka se změnami / dodatky","projects":types.get("procurement_with_changes",[])},
        "contract_with_changes":{"label":"Smlouva se změnami / dodatky","projects":types.get("contract_with_changes",[])},
        "contract":{"label":"Smlouva bez rozpoznané zakázky","projects":types.get("contract",[])},
        "other":{"label":"Ostatní záznamy","projects":types.get("other",[])},
        "unclassified":{"label":"Bez klasifikace","projects":types.get("unclassified",[])}
      },
      "projects":[{
          "id":p["id"],"title":p.get("title"),"status":p.get("status","unclassified"),
          "project_type":p.get("project_type") or p.get("canonical",{}).get("project_type","other"),
          "record_types":p.get("canonical",{}).get("lifecycle",{}).get("type_counts",{}),
          "source_count":len(p.get("sources",[])),
          "first_observed":p.get("canonical",{}).get("dates",{}).get("first_observed"),
          "last_observed":p.get("canonical",{}).get("dates",{}).get("last_observed"),
          "supplier_ico":p.get("canonical",{}).get("supplier_ico"),
          "procurement_signal":p.get("canonical",{}).get("procurement_signal",{"level":"none"})
      } for p in projects],
      "notes":[
        "Projects are created by the conservative cross-source resolver.",
        "A contractual addendum alone is not treated as evidence that a public tender was conducted.",
        "Project type is derived from documented source record types; it is separate from contractual status.",
        "Procurement signal is evidence-weighted metadata; explicit means the source text mentions procurement, likely means the contract appears procurement-related but does not prove the selection procedure."
        "Records without a reliable contractual status remain unclassified rather than being guessed."
      ]
    }
    INDEX.parent.mkdir(parents=True,exist_ok=True)
    INDEX.write_text(json.dumps(index,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Wrote {INDEX}: {len(projects)} projects")
if __name__=="__main__": main()
