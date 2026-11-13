"""Public profile onboarding with explicit separation of input and reviewed evidence."""
import hashlib,re
from urllib.parse import urlparse
from nexus.models import Company,Claim,utcnow,url_valid
from nexus.core.matching_engine import TAXONOMY

DOMAINS={"digital","marine","energy","environment"}
def register_company(repo,name,website,description,domains):
    name=name.strip();website=website.strip();description=description.strip()
    domains=list(dict.fromkeys(domains))
    if not 2<=len(name)<=120:
        raise ValueError("Company name must contain 2–120 characters")
    if not url_valid(website):
        raise ValueError("Provide the company's HTTPS website")
    if not 10<=len(description)<=3000:
        raise ValueError("Provide a public description of 10–3000 characters")
    if not domains or not set(domains)<=DOMAINS:
        raise ValueError("Select at least one supported application domain")
    host=urlparse(website).hostname.lower().removeprefix("www.")
    for existing in repo.companies():
        if existing.name.casefold()==name.casefold() or urlparse(existing.website).hostname.lower().removeprefix("www.")==host:
            raise ValueError("A profile with this company name or website already exists")
    slug=re.sub(r"[^a-z0-9]+","-",name.lower()).strip("-") or "company"
    identity=slug[:60]+"-"+hashlib.sha256(host.encode()).hexdigest()[:8]
    claim=Claim(text=description,category="description",classification="USER_INPUT",
        source_url=website,retrieved_at=utcnow(),confidence=0,
        verification_status="unreviewed",provenance="user_supplied")
    company=Company(identity,name,website,description,domains,claims=[claim],provenance="user_supplied")
    repo.save_company(company)
    return company

def add_reviewed_capability(repo,company_id,category,statement,source_url,excerpt,confirmed):
    if not confirmed:
        raise ValueError("Review the source and confirm it supports this statement")
    if category not in TAXONOMY:
        raise ValueError("Choose a supported capability category")
    if not statement.strip() or not excerpt.strip():
        raise ValueError("Provide a statement and its supporting source excerpt")
    if len(excerpt)>2000:
        raise ValueError("Keep the evidence excerpt under 2000 characters")
    claim=Claim(text=statement.strip(),category=category,source_url=source_url.strip(),
        excerpt=excerpt.strip(),retrieved_at=utcnow(),verification_status="source_reviewed",
        provenance="manual_source_review")
    company=repo.company(company_id)
    if any(c.text==claim.text and c.source_url==claim.source_url for c in company.claims):
        raise ValueError("This evidence claim is already stored")
    company.claims.append(claim)
    repo.save_company(company,expected_revision=company.revision)
    return company

