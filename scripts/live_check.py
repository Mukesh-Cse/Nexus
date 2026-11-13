"""Actual network attempts. Failure is reported, never converted to fake success."""
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from nexus.database.repository import Repository
from nexus.service import bootstrap,refresh_sources
from nexus.integrations.company_sources import CompanySources
from nexus.integrations.http import IntegrationError
from nexus.models import utcnow
from nexus.config import load_environment
load_environment(ROOT/".env")
repo=Repository(ROOT/"data"/"nexus.sqlite3")
bootstrap(repo)
result=refresh_sources(repo,"maritime cybersecurity",force=True)
try:
    page=CompanySources(repo).retrieve("https://cleura.com/")
    result["company_website"]={"status":"success","candidate_claims":len(page["claims"])}
except IntegrationError as exc:
    result["company_website"]={"status":"unavailable","message":str(exc)}
report={"executed_at":utcnow(),"services":result,"logs":repo.logs()}
(ROOT/"docs"/"live_integration_results.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
print(json.dumps(report,indent=2))
repo.close()

