"""Versioned SQLite repository. Parameterised queries and explicit tenant scope."""
import json
import sqlite3
from pathlib import Path
from nexus.models import Company, Record, utcnow

SCHEMA_VERSION = 1
SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY);
CREATE TABLE IF NOT EXISTS company (id TEXT PRIMARY KEY, payload TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS capability (id TEXT PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS evidence (id INTEGER PRIMARY KEY, company_id TEXT REFERENCES company(id) ON DELETE CASCADE,
 source_url TEXT NOT NULL, excerpt TEXT NOT NULL, retrieved_at TEXT NOT NULL, classification TEXT NOT NULL, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS company_capability (company_id TEXT REFERENCES company(id) ON DELETE CASCADE,
 capability_id TEXT REFERENCES capability(id), evidence_id INTEGER REFERENCES evidence(id) ON DELETE CASCADE,
 PRIMARY KEY(company_id,capability_id,evidence_id));
CREATE TABLE IF NOT EXISTS opportunity (id TEXT PRIMARY KEY, kind TEXT NOT NULL, payload TEXT NOT NULL, retrieved_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS research_publication (id TEXT PRIMARY KEY REFERENCES opportunity(id) ON DELETE CASCADE, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS funding_opportunity (id TEXT PRIMARY KEY REFERENCES opportunity(id) ON DELETE CASCADE, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS testbed (id TEXT PRIMARY KEY REFERENCES opportunity(id) ON DELETE CASCADE, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS recommendation (id TEXT PRIMARY KEY, company_id TEXT REFERENCES company(id), payload TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS collaboration_hypothesis (id TEXT PRIMARY KEY, payload TEXT NOT NULL, validation_status TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS company_profile_revision (id INTEGER PRIMARY KEY, company_id TEXT REFERENCES company(id),
 revision INTEGER NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(company_id,revision));
CREATE TABLE IF NOT EXISTS user_feedback (id INTEGER PRIMARY KEY, company_id TEXT REFERENCES company(id),
 recommendation_id TEXT NOT NULL, rating INTEGER CHECK(rating BETWEEN 1 AND 5), comment TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS private_note (id INTEGER PRIMARY KEY, tenant_id TEXT NOT NULL, content TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS retrieval_log (id INTEGER PRIMARY KEY, source TEXT NOT NULL, status TEXT NOT NULL,
 detail TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS api_cache (key TEXT PRIMARY KEY, payload TEXT NOT NULL, retrieved_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS ix_evidence_company ON evidence(company_id);
CREATE INDEX IF NOT EXISTS ix_opportunity_kind ON opportunity(kind);
CREATE INDEX IF NOT EXISTS ix_feedback_company ON user_feedback(company_id);
CREATE INDEX IF NOT EXISTS ix_private_tenant ON private_note(tenant_id);
"""
class Repository:
    def __init__(self, path="data/nexus.sqlite3"):
        self.path = str(path)
        if self.path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        from nexus.database.database import connect
        self.db,self.engine,self.proxy,self.backend = connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript(SCHEMA)
        versions = [r[0] for r in self.db.execute("SELECT version FROM schema_version")]
        if versions and max(versions) != SCHEMA_VERSION:
            raise RuntimeError("Unsupported database schema; migrate before opening")
        self.db.execute("INSERT OR IGNORE INTO schema_version VALUES (?)", (SCHEMA_VERSION,))
        self.db.commit()
    def close(self):
        if self.proxy is not None:
            self.proxy.close()
            self.engine.dispose()
        else:
            self.db.close()
    def companies(self):
        return [Company.from_dict(json.loads(r[0])) for r in self.db.execute("SELECT payload FROM company ORDER BY id")]
    def company(self, company_id):
        row = self.db.execute("SELECT payload FROM company WHERE id=?", (company_id,)).fetchone()
        if row is None:
            raise KeyError(company_id)
        return Company.from_dict(json.loads(row[0]))
    def save_company(self, company, expected_revision=None):
        """Optimistic update: public refinements are intentionally shared in this local demo."""
        with self.db:
            old = self.db.execute("SELECT payload FROM company WHERE id=?", (company.id,)).fetchone()
            previous = json.loads(old[0])["revision"] if old else -1
            if expected_revision is not None and previous != expected_revision:
                raise ValueError("Profile changed in another session. Reload before saving.")
            company.revision = previous + 1
            data = json.dumps(company.to_dict(), ensure_ascii=False)
            self.db.execute("INSERT INTO company VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload,updated_at=excluded.updated_at", (company.id, data, utcnow()))
            self.db.execute("INSERT INTO company_profile_revision(company_id,revision,payload,created_at) VALUES (?,?,?,?)", (company.id,company.revision,data,utcnow()))
            self.db.execute("DELETE FROM company_capability WHERE company_id=?", (company.id,))
            self.db.execute("DELETE FROM evidence WHERE company_id=?", (company.id,))
            for claim in company.claims:
                cur = self.db.execute("INSERT INTO evidence(company_id,source_url,excerpt,retrieved_at,classification,payload) VALUES (?,?,?,?,?,?)", (company.id,claim.source_url,claim.excerpt,claim.retrieved_at,claim.classification,json.dumps(claim.__dict__)))
                if claim.supported() and claim.category != "membership":
                    self.db.execute("INSERT OR IGNORE INTO capability VALUES (?,?)", (claim.category,claim.category))
                    self.db.execute("INSERT INTO company_capability VALUES (?,?,?)", (company.id,claim.category,cur.lastrowid))
            # Persisted recommendations are invalid after a profile update.
            self.db.execute("DELETE FROM recommendation")
            self.db.execute("DELETE FROM collaboration_hypothesis")
    def save_record(self, record):
        table = {"research":"research_publication","funding":"funding_opportunity","testbed":"testbed"}.get(record.kind)
        data = json.dumps(record.to_dict(), ensure_ascii=False)
        with self.db:
            self.db.execute("INSERT INTO opportunity VALUES (?,?,?,?) ON CONFLICT(id) DO UPDATE SET kind=excluded.kind,payload=excluded.payload,retrieved_at=excluded.retrieved_at", (record.id,record.kind,data,record.retrieved_at))
            if table:
                self.db.execute(f"INSERT INTO {table} VALUES (?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload", (record.id,data))
    def records(self):
        return [Record(**json.loads(r[0])) for r in self.db.execute("SELECT payload FROM opportunity ORDER BY id")]
    def save_recommendations(self, focus, recommendations):
        with self.db:
            self.db.execute("DELETE FROM recommendation WHERE company_id=?", (focus,))
            for rec in recommendations:
                rid = focus + ":" + rec["id"]
                payload = json.dumps(rec)
                self.db.execute("INSERT OR REPLACE INTO recommendation VALUES (?,?,?,?)", (rid,focus,payload,utcnow()))
                self.db.execute("INSERT OR REPLACE INTO collaboration_hypothesis VALUES (?,?,?)", (rid,payload,"hypothesis"))
    def feedback(self, company, rec_id, rating, comment):
        with self.db:
            self.db.execute("INSERT INTO user_feedback(company_id,recommendation_id,rating,comment,created_at) VALUES (?,?,?,?,?)", (company,rec_id,rating,comment[:2000],utcnow()))
    def feedback_rows(self):
        return [dict(r) for r in self.db.execute("SELECT * FROM user_feedback ORDER BY id DESC")]
    def log(self, source, status, detail):
        with self.db:
            self.db.execute("INSERT INTO retrieval_log(source,status,detail,created_at) VALUES (?,?,?,?)", (source,status,detail[:1000],utcnow()))
    def logs(self):
        return [dict(r) for r in self.db.execute("SELECT * FROM retrieval_log ORDER BY id DESC LIMIT 40")]
    def cache_get(self, key, max_age_hours=24):
        entry=self.cache_entry(key,max_age_hours)
        return entry["payload"] if entry else None
    def cache_entry(self, key, max_age_hours=24):
        from nexus.models import freshness
        row = self.db.execute("SELECT payload,retrieved_at FROM api_cache WHERE key=?", (key,)).fetchone()
        return {"payload":json.loads(row[0]),"retrieved_at":row[1]} if row and freshness(row[1], max_age_hours/24) else None
    def cache_put(self, key, value, retrieved_at=None):
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO api_cache VALUES (?,?,?)", (key,json.dumps(value),retrieved_at or utcnow()))
    def add_private_note(self, context, tenant, content):
        from nexus.security.privacy import require_tenant
        require_tenant(context, tenant)
        with self.db:
            self.db.execute("INSERT INTO private_note(tenant_id,content) VALUES (?,?)", (tenant,content))
    def private_notes(self, context, tenant):
        from nexus.security.privacy import require_tenant
        require_tenant(context, tenant)
        return [r[0] for r in self.db.execute("SELECT content FROM private_note WHERE tenant_id=?", (tenant,))]

