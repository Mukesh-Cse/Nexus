"""Explicit, inspectable agent workflow; no LLM needed for ranking."""
from pathlib import Path
import json,os,time,threading
from nexus.models import Company,Record
from nexus.core.matching_engine import discover
from nexus.integrations.http import CachedHTTP,IntegrationError
from nexus.integrations.openalex import OpenAlex
from nexus.integrations.vinnova import Vinnova
from nexus.security.boundary_guard import route_request

def bootstrap(repo):
    if repo.companies():
        return
    path=Path(__file__).resolve().parents[1]/"data"/"public_snapshot.json"
    data=json.loads(path.read_text(encoding="utf-8"))
    for company in data["companies"]:
        repo.save_company(Company.from_dict(company))
    for record in data["records"]:
        repo.save_record(Record(**record))
    repo.log("public_snapshot","snapshot_import","Manually reviewed public pages; not a live API response. Retrieval 2026-11-13.")

_refresh_lock=threading.Lock()
_public_next_refresh=0.

def refresh_sources(repo,query,sources=None,force=False,since=None,pages=1,public_demo=False):
    global _public_next_refresh
    sources=["OpenAlex","Vinnova"] if sources is None else list(dict.fromkeys(sources))
    if not set(sources)<={"OpenAlex","Vinnova"}:
        raise ValueError("Choose OpenAlex or Vinnova")
    if public_demo:
        if os.getenv("NEXUS_ALLOW_PUBLIC_REFRESH","0")!="1":
            return {name:{"status":"disabled","message":"The host has not enabled public API refresh."} for name in sources}
        with _refresh_lock:
            remaining=_public_next_refresh-time.monotonic()
            if remaining>0:
                return {name:{"status":"cooldown","retry_after":int(remaining)+1,"message":"The public demo allows one refresh batch per minute."} for name in sources}
            _public_next_refresh=time.monotonic()+60
        force=False
        pages=1
    http=CachedHTTP(repo)
    outcome={}
    connectors={"OpenAlex":lambda:OpenAlex(http).search(query,pages=pages,refresh=force),
                "Vinnova":lambda:Vinnova(http).search(since=since,refresh=force)}
    for name in sources:
        try:
            records=connectors[name]()
            for record in records:
                repo.save_record(record)
            outcome[name]={"status":("cached" if http.last_origin=="cache" else "live") if records else "empty",
                "records":len(records),"retrieved_at":http.last_retrieved_at,
                "message":"Public records stored; matching can use the updated evidence." if records else "The API returned no valid records for this search."}
        except (IntegrationError,ValueError) as exc:
            outcome[name]={"status":"unavailable","records":0,"code":getattr(exc,"code","invalid_input"),
                "retry_after":getattr(exc,"retry_after",None),"message":str(exc)}
    return outcome

def workflow(repo,focus_id,request="",live=False,weights=None,public_demo=False):
    boundary=route_request(request) if request else {"status":"supported","message":""}
    if boundary["status"]!="supported":
        return {"boundary":boundary,"recommendations":[],"refresh":{}}
    focus=repo.company(focus_id)
    live_query=(request or " ".join([focus.priority,*focus.capabilities(),*focus.domains])).replace("_"," ")[:300]
    updates=refresh_sources(repo,live_query,public_demo=public_demo) if live else {}
    recs=discover(focus,repo.companies(),repo.records(),weights=weights)
    # Verification step gates persisted outputs.
    valid=[]
    for rec in recs:
        if rec["classification"]=="HYPOTHESIS" and rec["relationships"] and rec["scores"]["E"]>0:
            valid.append(rec)
    repo.save_recommendations(focus_id,valid)
    return {"boundary":boundary,"recommendations":valid,"refresh":updates}

