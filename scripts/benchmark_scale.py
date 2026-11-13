"""Bounded-candidate timing on synthetic copies; not a production load test."""
import sys,json,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from nexus.database.repository import Repository
from nexus.models import Company,utcnow
from nexus.service import bootstrap
from nexus.core.matching_engine import discover
repo=Repository(":memory:")
bootstrap(repo)
base=repo.companies()
companies=[]
for i in range(40):
    d=base[i%len(base)].to_dict()
    d["id"]=f"synthetic-{i:02d}"
    d["name"]=f"Synthetic capability fixture {i}"
    companies.append(Company.from_dict(d))
start=time.perf_counter()
results=discover(companies[0],companies,repo.records())
elapsed=time.perf_counter()-start
report={"executed_at":utcnow(),"fixture":"40 synthetic copies of the four capability profiles; not additional real member companies",
 "focal_searches":1,"companies":40,"returned_recommendations":len(results),
 "elapsed_seconds":round(elapsed,4),"candidate_partner_bound":12,"triple_partner_bound":8,
 "interpretation":"Single-process local timing only; excludes retrieval, embeddings downloads, concurrent users and browser rendering."}
(ROOT/"docs"/"scale_benchmark.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
print(json.dumps(report,indent=2))
repo.close()

