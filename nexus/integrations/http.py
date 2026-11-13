"""Bounded HTTP client with honest cache timestamps and sanitised errors."""
import hashlib,json,time
from datetime import datetime,timezone
import requests
from nexus.models import utcnow

class IntegrationError(RuntimeError):
    def __init__(self,message,code="unavailable",retry_after=None):
        super().__init__(message)
        self.code=code
        self.retry_after=retry_after

def _error(response):
    status=response.status_code
    messages={
        401:"Authentication failed. Check the configured API key.",
        403:"Access was denied. Check key activation and source permissions.",
        404:"The official API endpoint or requested record was not found.",
        429:"The source rate limit or daily quota was reached. Try again later.",
        500:"The source API returned a server error.",
        502:"The source API gateway is unavailable.",
        503:"The source API is temporarily unavailable."
    }
    retry=None
    raw=response.headers.get("Retry-After","")
    try:retry=max(0,int(raw))
    except (ValueError,TypeError):pass
    return IntegrationError(messages.get(status,f"The source returned HTTP {status}."),
        code=f"http_{status}",retry_after=retry)

class CachedHTTP:
    def __init__(self,repo,session=None):
        self.repo=repo
        self.session=session or requests.Session()
        self.last_retrieved_at=None
        self.last_origin=None
    def json(self,url,params=None,headers=None,refresh=False):
        fingerprint=json.dumps({"url":url,"params":params or {},"headers":headers or {}},sort_keys=True)
        key=hashlib.sha256(fingerprint.encode()).hexdigest()
        entry=None if refresh else self.repo.cache_entry(key)
        source=url.split("?",1)[0]
        if entry is not None:
            self.last_retrieved_at=entry["retrieved_at"]
            self.last_origin="cache"
            self.repo.log(source,"cached","Reused response with original retrieval timestamp")
            return entry["payload"]
        request_headers={"User-Agent":"NEXUS-InnovationPrototype/1.0","Accept":"application/json",**(headers or {})}
        try:
            for attempt in range(2):
                response=self.session.get(url,params=params,headers=request_headers,timeout=(8,25))
                status=response.status_code
                if status in {429,503}:
                    error=_error(response)
                    if attempt==0 and error.retry_after is not None and error.retry_after<=2:
                        time.sleep(error.retry_after)
                        continue
                    raise error
                if isinstance(status,int) and status>=400:
                    raise _error(response)
                response.raise_for_status()
                if len(response.content)>10_000_000:
                    raise IntegrationError("The source response exceeds the 10 MB limit.","response_limit")
                data=response.json()
                if not isinstance(data,(dict,list)):
                    raise IntegrationError("The source did not return a JSON object or list.","invalid_json")
                stamp=utcnow()
                self.repo.cache_put(key,data,retrieved_at=stamp)
                self.last_retrieved_at=stamp
                self.last_origin="live"
                self.repo.log(source,"live_success","Live HTTP response validated and cached")
                return data
        except IntegrationError as exc:
            self.repo.log(source,"failed",exc.code+": "+str(exc))
            raise
        except (requests.RequestException,ValueError) as exc:
            code="invalid_json" if isinstance(exc,ValueError) else "network_error"
            self.repo.log(source,"failed",code+": "+type(exc).__name__)
            raise IntegrationError("Network access failed or the source response was invalid. Existing records are retained.",code) from None

