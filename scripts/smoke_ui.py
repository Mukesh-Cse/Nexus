"""Execute every Streamlit view and verify a real profile edit survives rerun."""
import sys,os,tempfile,json
import asyncio
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
test_temp=ROOT/'data'/'test_tmp'
assert test_temp.resolve().is_relative_to(ROOT)
test_temp.mkdir(parents=True,exist_ok=True)
tempfile.tempdir=str(test_temp)
from nexus.models import utcnow
from streamlit.testing.v1 import AppTest
socket_free='--socket-free' in sys.argv
public_demo='--public-demo' in sys.argv
if public_demo: os.environ['NEXUS_PUBLIC_DEMO']='1'
if socket_free:
    class ScriptOnlyLoop(asyncio.AbstractEventLoop):
        """Test adapter: AppTest's synchronous ScriptRunner needs a loop identity only.
        This deliberately does not implement real asynchronous or network execution.
        """
        def __init__(self): self.closed=False
        def close(self): self.closed=True
        def is_closed(self): return self.closed
        def is_running(self): return False
        def get_debug(self): return False
        def call_soon_threadsafe(self,callback,*args,context=None):
            return callback(*args)
    asyncio.new_event_loop=ScriptOnlyLoop
pages=["Innovation Overview","Company DNA","Innovation Graph","Opportunity Radar","Innovation Blueprint","Evaluation & Quality"]
results=[]
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
    os.environ["NEXUS_DB"]=str(Path(directory)/"ui.sqlite3")
    app=AppTest.from_file(str(ROOT/"app.py"),default_timeout=60).run()
    for page in pages:
        app.sidebar.radio[0].set_value(page).run()
        errors=[e.message for e in app.exception]
        results.append({"page":page,"exceptions":errors})
        if errors:
            print(errors)
    app.sidebar.radio[0].set_value("Company DNA").run()
    next(x for x in app.text_input if x.label=="Public innovation priority").set_value("Maritime monitoring pilot")
    next(b for b in app.button if b.label=="Save profile & recalculate").click().run()
    value=next(x for x in app.text_input if x.label=="Public innovation priority").value
    results.append({"profile_edit_persisted":value=="Maritime monitoring pilot","ok":value=="Maritime monitoring pilot","exceptions":[e.message for e in app.exception]})
    changes={"Complementarity weight (%)":60,"Funding relevance weight (%)":0,"Research relevance weight (%)":0,"Evidence quality weight (%)":40}
    for label,amount in changes.items():
        next(x for x in app.number_input if x.label==label).set_value(amount)
    next(b for b in app.button if b.label=="Apply ranking weights").click().run()
    results.append({"action":"Change ranking weights","ok":app.session_state["ranking_weights"]=={"C":.6,"O":0.,"R":0.,"E":.4},"exceptions":[e.message for e in app.exception]})
    if not public_demo:
        next(x for x in app.text_input if x.label=="Company name").set_value("Synthetic UI company")
        next(x for x in app.text_input if x.label=="Company HTTPS website").set_value("https://example.org")
        next(x for x in app.text_area if x.label=="Public company description").set_value("Synthetic company created by the automated UI onboarding check.")
        next(b for b in app.button if b.label=="Create company profile").click().run()
        from nexus.database.repository import Repository
        check=Repository(os.environ["NEXUS_DB"])
        created=next(c for c in check.companies() if c.name=="Synthetic UI company")
        check.close()
        app.sidebar.selectbox[0].select(created.id).run()
        next(x for x in app.selectbox if x.label=="Capability category").select("software")
        next(x for x in app.text_input if x.label=="Evidence-backed capability statement").set_value("Synthetic software capability for UI testing")
        next(x for x in app.text_input if x.label=="Supporting HTTPS source URL").set_value("https://example.org/synthetic-fixture")
        next(x for x in app.text_area if x.label=="Supporting excerpt").set_value("Synthetic source excerpt used only by automated UI tests.")
        next(x for x in app.checkbox if x.label=="I checked that this public source supports the statement.").set_value(True)
        next(b for b in app.button if b.label=="Save reviewed capability").click().run()
        check=Repository(os.environ["NEXUS_DB"])
        reviewed=check.company(created.id)
        check.close()
        results.append({"action":"Register company and save reviewed evidence","ok":"software" in reviewed.capabilities(),"exceptions":[e.message for e in app.exception]})
    if not public_demo:
        from unittest.mock import Mock,patch
        from tests.test_live_apis import WORK,CALL,response
        app.sidebar.radio[0].set_value("Opportunity Radar").run()
        next(x for x in app.text_input if x.label=="OpenAlex research query").set_value("marine cybersecurity")
        session=Mock()
        session.get.side_effect=lambda url,**kwargs: response({"results":[WORK],"meta":{}} if "openalex" in url else [CALL])
        with patch("nexus.integrations.http.requests.Session",return_value=session):
            next(b for b in app.button if b.label=="Refresh selected APIs").click().run()
        outcomes=app.session_state["api_results"]
        check=Repository(os.environ["NEXUS_DB"])
        imported=[r for r in check.records() if r.id in {"W999001","vinnova:2026-12345"}]
        check.close()
        results.append({"action":"Refresh selected APIs button (mocked HTTP, no real network)",
            "ok":len(imported)==2 and all(r.provenance=="live_api" for r in imported) and all(v["status"]=="live" for v in outcomes.values()),
            "exceptions":[e.message for e in app.exception]})
    # AppTest executes in its own module context. Do not import app.py a second time.
report={"executed_at":utcnow(),"public_demo":public_demo,"method":"Streamlit AppTest with script-only loop adapter; real script and widgets, no server or asynchronous/network execution" if socket_free else "Streamlit AppTest; not browser visual inspection","results":results}
(ROOT/"docs"/("public_demo_ui_results.json" if public_demo else "ui_test_results.json")).write_text(json.dumps(report,indent=2),encoding="utf-8")
print(json.dumps(report,indent=2))
sys.exit(1 if any(r.get("exceptions") or r.get("ok") is False for r in results) else 0)

