import re
from datetime import datetime,timedelta,timezone
from urllib.parse import urlparse
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup
from nexus.models import Record,utcnow,url_valid
from nexus.security.boundary_guard import safe_source_text
from nexus.integrations.http import IntegrationError
from nexus.core.matching_engine import normalise

def text(value):
    return safe_source_text(BeautifulSoup(str(value or ""),"html.parser").get_text(" ",strip=True))

def stockholm_time(value):
    if not value:return ""
    d=datetime.fromisoformat(value)
    return (d.replace(tzinfo=ZoneInfo("Europe/Stockholm")) if not d.tzinfo else d).isoformat()

def parse_call(item,retrieved_at=None,provenance="live_api"):
    identity=item["Diarienummer"]
    if not re.fullmatch(r"\d{4}-\d{5}",identity):
        raise ValueError("Invalid call ID")
    title=text(item.get("Titel")) or text(item.get("TitelEngelska"))
    description=text(item.get("Beskrivning")) or text(item.get("BeskrivningEngelska"))
    if not title:
        raise ValueError("Call title missing")
    texts=item.get("WebTextLista") or []
    eligibility=" ".join(text(x.get("TextEn") or x.get("TextSv")) for x in texts if str(x.get("TextID"))=="2")
    if item.get("Publik")==0:
        eligibility="Invitation-only round. "+eligibility
    source="https://data.vinnova.se/api/ansokningsomgangar/"+identity
    for link in item.get("LankLista") or []:
        candidate=link.get("URL","")
        host=urlparse(candidate).hostname or ""
        if url_valid(candidate) and host in {"vinnova.se","www.vinnova.se"}:
            source=candidate
            break
    return Record(id="vinnova:"+identity,kind="funding",title=title,description=description,
        source_url=source,retrieved_at=retrieved_at or utcnow(),
        opens_at=stockholm_time(item.get("Oppningsdatum")),deadline=stockholm_time(item.get("Stangningsdatum")),
        eligibility=eligibility or "Not supplied; review the full call text.",
        tags=normalise(title+" "+description+" "+eligibility),provenance=provenance)

class Vinnova:
    def __init__(self,http):
        self.http=http
    def search(self,since=None,refresh=False):
        since=since or (datetime.now(timezone.utc).date()-timedelta(days=90)).isoformat()
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}",since):
            raise ValueError("Expected ISO update date")
        datetime.fromisoformat(since)
        data=self.http.json("https://data.vinnova.se/api/ansokningsomgangar/"+since,refresh=refresh)
        if not isinstance(data,list):
            raise IntegrationError("Unexpected Vinnova response; existing calls were retained.","schema_error")
        stamp=getattr(self.http,"last_retrieved_at",None)
        stamp=stamp if isinstance(stamp,str) else None
        provenance="cached_api" if getattr(self.http,"last_origin",None)=="cache" else "live_api"
        records={}
        if len(data)>500:
            self.http.repo.log("Vinnova","bounded_result","Parsed the first 500 application rounds; narrow the update date to inspect more.")
        for item in data[:500]:
            try:
                record=parse_call(item,stamp,provenance)
                records[record.id]=record
            except (KeyError,TypeError,ValueError,AttributeError):
                self.http.repo.log("Vinnova","parse_rejected","Malformed or incomplete public application round")
        return list(records.values())

