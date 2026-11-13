"""Developer-authored synthetic benchmark, never represented as human validation."""
from itertools import combinations
import json
from pathlib import Path
from nexus.models import Company,Claim
from nexus.core.matching_engine import complementarity
from nexus.core.embeddings import similarity

def evaluate():
    path=Path(__file__).resolve().parents[2]/"data"/"evaluation_pairs.json"
    data=json.loads(path.read_text(encoding="utf-8"))
    lookup={}
    for p in data["profiles"]:
        claims=[Claim(text=cap,category=cap,source_url="https://example.org/synthetic-benchmark",excerpt="Synthetic test fixture",retrieved_at="2026-11-13T00:00:00+00:00",provenance="synthetic_fixture") for cap in p["capabilities"]]
        lookup[p["id"]]=Company(p["id"],p["id"],"https://example.org",p["description"],p["domains"],claims)
    rows=[]
    for item in data["pairs"]:
        a,b=lookup[item["a"]],lookup[item["b"]]
        rows.append({**item,"complementarity":complementarity(a,b),"similarity":similarity(a.public_text(),b.public_text())})
    output={}
    positives=sum(r["relevant"] for r in rows)
    for method in ["complementarity","similarity"]:
        ranked=sorted(rows,key=lambda r:(-r[method],r["a"],r["b"]))
        top=ranked[:5]
        output[method]={"precision_at_5":sum(r["relevant"] for r in top)/5,
            "recall_at_5":sum(r["relevant"] for r in top)/positives if positives else None,
            "top_5":[r["a"]+"+"+r["b"] for r in top]}
    output["ranking_differentiation"]=1-len(set(output["complementarity"]["top_5"])&set(output["similarity"]["top_5"]))/5
    return {"label_source":"Developer-authored synthetic labels; no human raters or held-out population. This is an algorithm sanity check.",
            "candidate_count":len(rows),"positive_count":positives,"metrics":output,"rows":rows}

