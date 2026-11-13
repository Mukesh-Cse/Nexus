"""Validated domain records; no network or UI dependencies."""
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from urllib.parse import urlparse
import re

def utcnow():
    return datetime.now(timezone.utc).isoformat()

def url_valid(url):
    try:
        p = urlparse(url)
        return p.scheme == "https" and bool(p.hostname) and not p.username and not p.password
    except ValueError:
        return False

def parsed_time(value):
    if not value:
        return None
    try:
        d = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None

def freshness(value, days=90, now=None):
    dt = parsed_time(value)
    return bool(dt and 0 <= ((now or datetime.now(timezone.utc)) - dt).total_seconds() <= days * 86400)

@dataclass
class Claim:
    text: str
    category: str
    source_url: str = ""
    excerpt: str = ""
    retrieved_at: str = ""
    classification: str = "FACT"
    confidence: float = 1.0
    verification_status: str = "source_reviewed"
    provenance: str = "public_snapshot"
    def __post_init__(self):
        if self.classification not in {"FACT", "INFERENCE", "USER_INPUT"}:
            raise ValueError("Invalid classification")
        if not 0 <= self.confidence <= 1:
            raise ValueError("Confidence must be between 0 and 1")
        if self.classification == "FACT" and not (
            url_valid(self.source_url) and self.excerpt.strip() and parsed_time(self.retrieved_at)
        ):
            raise ValueError("Facts require an HTTPS source, supporting excerpt and retrieval time")
        if not self.text.strip() or len(self.text) > 6000:
            raise ValueError("Claim text must contain 1–6000 characters")
    def supported(self):
        return self.classification == "FACT" and self.verification_status == "source_reviewed"

@dataclass
class Company:
    id: str
    name: str
    website: str
    description: str
    domains: list
    claims: list = field(default_factory=list)
    interests: list = field(default_factory=list)
    priority: str = ""
    revision: int = 0
    provenance: str = "public_snapshot"
    def capabilities(self):
        return sorted({c.category for c in self.claims if c.supported() and c.category != "membership"})
    def public_text(self):
        return " ".join([self.description, *self.capabilities(), *self.domains])
    def to_dict(self):
        return asdict(self)
    @classmethod
    def from_dict(cls, d):
        d = dict(d)
        d["claims"] = [Claim(**c) for c in d.get("claims", [])]
        return cls(**d)

@dataclass
class Record:
    id: str
    kind: str
    title: str
    description: str
    source_url: str
    retrieved_at: str
    publication_date: str = ""
    authors: list = field(default_factory=list)
    tags: list = field(default_factory=list)
    deadline: str = ""
    opens_at: str = ""
    eligibility: str = ""
    provenance: str = "public_snapshot"
    def __post_init__(self):
        if self.kind not in {"research", "funding", "testbed", "programme"}:
            raise ValueError("Unknown record kind")
        if not url_valid(self.source_url) or not parsed_time(self.retrieved_at):
            raise ValueError("Record requires a valid HTTPS source and retrieval time")
    def status(self, now=None):
        if self.kind != "funding":
            return "reference"
        now = now or datetime.now(timezone.utc)
        end, start = parsed_time(self.deadline), parsed_time(self.opens_at)
        if end and now >= end:
            return "closed"
        if start and now < start:
            return "upcoming"
        if not freshness(self.retrieved_at, 30, now):
            return "unknown · stale source"
        return "open" if end and start else "unknown"
    def to_dict(self):
        return asdict(self)

