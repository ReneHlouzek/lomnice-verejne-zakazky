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
    for p in projects:
        status=p.get("status") or "unclassified"
        if status in buckets: buckets[status].append(p["id"])
    index={
      "schema_version":2,
      "parser_state":"resolved" if projects else "awaiting-source-data",
      "generated_at":datetime.now(timezone.utc).isoformat(),
      "source":CONFIG["source"],
      "counts":{k:len(v) for k,v in buckets.items()},
      "total_projects":len(projects),
      "statuses":{k:{"label":v,"projects":buckets[k]} for k,v in statuses.items()},
      "projects":[{"id":p["id"],"title":p.get("title"),"status":p.get("status","unclassified"),"source_count":len(p.get("sources",[]))} for p in projects],
      "notes":["Projects are created by the conservative cross-source resolver.","Records without a reliable status remain unclassified rather than being guessed."]
    }
    INDEX.parent.mkdir(parents=True,exist_ok=True)
    INDEX.write_text(json.dumps(index,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Wrote {INDEX}: {len(projects)} projects")
if __name__=="__main__": main()
