import os,re
from nexus.models import Record,utcnow
from nexus.security.boundary_guard import safe_source_text
from nexus.integrations.http import IntegrationError
from nexus.core.matching_engine import normalise

def parse_work(w,retrieved_at=None,provenance="live_api"):
    if not isinstance(w,dict) or not re.fullmatch(r"https://openalex.org/W[0-9]+",w.get("id","")):
        raise ValueError("OpenAlex work lacks a canonical identifier")
    title=w.get("display_name") or w.get("title")
    if not isinstance(title,str) or not title.strip():
        raise ValueError("OpenAlex work lacks a title")
    index=w.get("abstract_inverted_index") or {}
    positions=sorted((pos,word) for word,locations in index.items() for pos in locations)
    abstract=" ".join(word for _,word in positions)[:5000]
    topics=[t["display_name"].lower() for t in (w.get("topics") or []) if isinstance(t,dict) and t.get("display_name")]
    tags=set(topics)|set(normalise(title+" "+abstract+" "+" ".join(topics)))
    if re.search(r"marine|maritime|underwater",title+" "+abstract,re.I):
        tags.add("marine")
    return Record(id=w["id"].rsplit("/",1)[-1],kind="research",
        title=safe_source_text(title),description=safe_source_text(abstract),
        authors=[a["author"]["display_name"] for a in (w.get("authorships") or []) if isinstance(a,dict) and (a.get("author") or {}).get("display_name")],
        publication_date=w.get("publication_date") or "",source_url=w["id"],
        retrieved_at=retrieved_at or utcnow(),tags=sorted(tags),provenance=provenance)

class OpenAlex:
    def __init__(self,http):
        self.http=http
    def search(self,query,pages=1,refresh=False):
        if not query.strip() or len(query)>300:
            raise ValueError("Research query must contain 1–300 characters")
        key=os.getenv("OPENALEX_API_KEY","").strip()
        page_limit=min(max(pages,1),3) if key else 1
        cursor="*"
        records={}
        for _ in range(page_limit):
            params={"search":query.strip(),"per_page":5,
                    "select":"id,display_name,authorships,publication_date,abstract_inverted_index,topics"}
            headers={}
            if key:
                headers["Authorization"]="Bearer "+key
                params["cursor"]=cursor
            else:
                params["page"]=1
            data=self.http.json("https://api.openalex.org/works",params,headers=headers,refresh=refresh)
            if not isinstance(data,dict) or not isinstance(data.get("results"),list):
                raise IntegrationError("Unexpected OpenAlex response.","schema_error")
            stamp=getattr(self.http,"last_retrieved_at",None)
            stamp=stamp if isinstance(stamp,str) else None
            provenance="cached_api" if getattr(self.http,"last_origin",None)=="cache" else "live_api"
            for work in data["results"]:
                try:
                    record=parse_work(work,stamp,provenance)
                    records[record.id]=record
                except (ValueError,KeyError,TypeError,AttributeError):
                    self.http.repo.log("OpenAlex","parse_rejected","Publication lacks valid source metadata")
            next_cursor=(data.get("meta") or {}).get("next_cursor")
            if not key or not next_cursor or next_cursor==cursor:
                break
            cursor=next_cursor
        if not key and pages>1:
            self.http.repo.log("OpenAlex","paging_limited","Anonymous query retrieved one page; a verified key enables cursor pagination.")
        return list(records.values())

