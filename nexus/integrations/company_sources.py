"""Allowlisted public websites; robots enforced, no auth bypass or arbitrary hosts."""
import ipaddress
import os
import socket
from urllib.parse import urlparse,urljoin
from urllib.robotparser import RobotFileParser
import requests
from bs4 import BeautifulSoup
from nexus.models import Claim, utcnow, url_valid
from nexus.core.matching_engine import normalise
from nexus.security.boundary_guard import safe_source_text
from nexus.integrations.http import IntegrationError

DEFAULT_HOSTS={"www.bluesciencepark.se","bluesciencepark.se","malvacom.com","www.malvacom.com",
 "cleura.com","www.cleura.com","www.dnv.com","dnv.com","balticoffshore.se","www.balticoffshore.se"}
AGENT="NexusResearchPrototype/1.0"
def validate_source_url(url):
    if not url_valid(url):
        raise ValueError("Only public HTTPS URLs are accepted")
    p=urlparse(url)
    allowed=DEFAULT_HOSTS|set(filter(None,os.getenv("NEXUS_SOURCE_HOSTS","").split(",")))
    if p.hostname not in allowed or p.port not in (None,443):
        raise ValueError("Host must be explicitly allowlisted in NEXUS_SOURCE_HOSTS")
    addresses=socket.getaddrinfo(p.hostname,443,type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise ValueError("Private, local or reserved hosts are forbidden")

def extract_claims(text,url,retrieved_at=None):
    text=safe_source_text(text)
    claims=[]
    for sentence in re_split(text):
        if not 20<=len(sentence)<=1000:
            continue
        for category in normalise(sentence):
            if category not in {c.category for c in claims}:
                claims.append(Claim(text=sentence[:600],category=category,source_url=url,excerpt=sentence,
                    retrieved_at=retrieved_at or utcnow(),verification_status="pending_review",provenance="website_extraction"))
    return claims

def re_split(text):
    import re
    return re.split(r"[\n.!?]+",text)

class CompanySources:
    def __init__(self,repo,session=None):
        self.repo=repo
        self.session=session or requests.Session()
    def _get(self,url):
        validate_source_url(url)
        response=self.session.get(url,headers={"User-Agent":AGENT},timeout=(5,12),allow_redirects=False,stream=True)
        # Redirects are rejected so an approved site cannot redirect to an internal service.
        if 300<=response.status_code<400:
            raise IntegrationError("Redirect rejected. Use the final official HTTPS URL.")
        response.raise_for_status()
        chunks=[]; size=0
        for chunk in response.iter_content(16384):
            size+=len(chunk)
            if size>2_000_000:
                raise IntegrationError("Page exceeds the 2 MB limit")
            chunks.append(chunk)
        return b"".join(chunks).decode(response.encoding or "utf-8",errors="replace")
    def retrieve(self,url):
        try:
            root=urlparse(url)
            robots_url=f"https://{root.netloc}/robots.txt"
            robot_text=self._get(robots_url)
            robot=RobotFileParser()
            robot.parse(robot_text.splitlines())
            if not robot.can_fetch(AGENT,url):
                raise IntegrationError("robots.txt disallows this page")
            page=self._get(url)
            soup=BeautifulSoup(page,"html.parser")
            for tag in soup(["script","style","nav","header","footer","form"]):
                tag.decompose()
            main=soup.find("main") or soup
            text=safe_source_text(main.get_text(" ",strip=True))
            self.repo.log(url,"live_success","Retrieved public page after robots check")
            return {"url":url,"text":text,"retrieved_at":utcnow(),"claims":extract_claims(text,url)}
        except (requests.RequestException,OSError,ValueError,IntegrationError) as exc:
            self.repo.log(url,"failed",type(exc).__name__+"; page not imported")
            raise IntegrationError("Website could not be retrieved safely. Check robots, final URL and network access.") from exc

