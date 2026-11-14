from pathlib import Path
import html, json, os, importlib.util
from datetime import datetime,timedelta,timezone
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from nexus.database.repository import Repository
from nexus.database.workspace import session_repository
from nexus.company_profiles import register_company,add_reviewed_capability
from nexus.core.matching_engine import TAXONOMY
from nexus.core.scoring import WEIGHTS
from nexus.models import Claim, freshness, utcnow
from nexus.service import bootstrap,workflow,refresh_sources
from nexus.core.matching_engine import baseline,relevance
from nexus.core.embeddings import backend
from nexus.core.blueprint_generator import generate
from nexus.core.graph_engine import graph_data,graph_html,plotly_figure,COLORS
from nexus.core.evaluation import evaluate
from nexus.integrations.company_sources import CompanySources
from nexus.integrations.http import IntegrationError
from nexus.integrations.llm import explain
from nexus.config import load_environment,CONFIG_KEYS,credential_status
from nexus.directory import import_directory,metadata_rows
from streamlit.errors import StreamlitSecretNotFoundError

ROOT=Path(__file__).parent
load_environment(ROOT/".env")
try:
    for key in CONFIG_KEYS:
        if not os.getenv(key) and key in st.secrets:
            os.environ[key]=str(st.secrets[key])
except (FileNotFoundError,StreamlitSecretNotFoundError):
    pass
PUBLIC_DEMO=os.getenv("NEXUS_PUBLIC_DEMO","0")=="1"
ALLOW_LIVE=not PUBLIC_DEMO or os.getenv("NEXUS_ALLOW_PUBLIC_REFRESH","0")=="1"
st.set_page_config(page_title="NEXUS · Innovation Intelligence",page_icon="◈",layout="wide",initial_sidebar_state="expanded")
st.markdown("""<style>
:root{--navy:#08111f;--panel:#101d30;--cyan:#55deeb;--muted:#99acc6}
.stApp{background:#08111f;color:#e5eefc}
[data-testid="stSidebar"]{background:#0b1626;border-right:1px solid #1d3049}
.block-container{padding:2.5rem 3rem 4rem;max-width:1580px}
h1{font-size:2.6rem!important;letter-spacing:-1.4px;font-weight:650!important}
h2,h3{letter-spacing:-.45px}p{line-height:1.65}
[data-testid="stMetric"]{background:#101d30;border:1px solid #243752;padding:18px;border-radius:12px}
[data-testid="stMetricLabel"]{color:#a4b6cf}
[data-testid="stMetricValue"]{font-size:2rem;color:#e9f4ff}
[data-testid="stVerticalBlockBorderWrapper"]>div{border-color:#25364f!important;border-radius:12px}
.stButton>button[kind="primary"],.stFormSubmitButton>button[kind="primary"]{background:#367cf1;border:0}
.kicker{font-size:11px;font-weight:700;letter-spacing:2px;color:#55deeb;margin:8px 0}
.brand{font-size:30px;font-weight:800;letter-spacing:5px;color:#f2f7ff}
.brand-sub{font-size:10px;letter-spacing:1.7px;color:#849ab9;margin-bottom:28px}
.hero{padding:22px 28px;background:linear-gradient(110deg,#10233e,#0e1b2e);border:1px solid #29405d;border-radius:14px;margin-bottom:24px}
.hero h2{font-size:26px;margin:0}.hero p{color:#a8bbd3;max-width:780px}
.chip{display:inline-block;padding:4px 10px;border:1px solid #28556a;border-radius:30px;color:#6ee0df;font-size:11px;margin:3px}
.caption-label{color:#89a1be;font-size:11px;letter-spacing:1.4px}
hr{border-color:#22334c!important}
</style>""",unsafe_allow_html=True)

@st.cache_resource
def repository(path):
    r=Repository(path)
    bootstrap(r)
    import_directory(r)
    return r
repo=session_repository(st.session_state) if PUBLIC_DEMO else repository(os.getenv("NEXUS_DB") or str(ROOT/"data"/"nexus.sqlite3"))
companies=repo.companies()
records=repo.records()

with st.sidebar:
    st.markdown('<div class="brand">◈ NEXUS</div><div class="brand-sub">INNOVATION CONNECTION ENGINE</div>',unsafe_allow_html=True)
    st.caption("BLUE SCIENCE PARK · PROTOTYPE")
    page=st.radio("Workspace",["Innovation Overview","Member Directory","Company DNA","Innovation Graph","Opportunity Radar","Innovation Blueprint","Evaluation & Quality"],label_visibility="collapsed")
    st.divider()
    focus_id=st.selectbox("Company perspective",[c.id for c in companies],format_func=lambda cid:next(c.name for c in companies if c.id==cid))
    st.caption("Public demo - changes stay in this browser session" if PUBLIC_DEMO else "Local single-user workspace - public profiles only")
    st.divider()
    st.caption("INTELLIGENCE MODE")
    api_records=[r for r in records if r.provenance in {"live_api","cached_api"}]
    st.markdown("**Stored API records + snapshots**" if api_records else "**Source-reviewed snapshots**")
    st.caption(str(len(api_records))+" API records stored")
    st.caption("Public pages checked 13 Nov 2026. Snapshots remain available when APIs are offline.")
    st.caption("Matching: "+backend())
    st.caption("Private interactions are unavailable until authenticated tenancy is configured.")
    st.caption(str(sum(bool(c.directory_profile) for c in companies))+" directory profiles · wider ecosystem coverage unknown")
    st.caption("Equally scored collaborators prefer a shared published city, then a shared Blekinge location. Core C/O/R/E scores are unchanged.")
    with st.expander("API connections"):
        status=credential_status()
        st.caption("OpenAlex: "+("key configured" if status["OpenAlex key"] else "anonymous first-page access"))
        st.caption("Vinnova: public application-round API")
        st.caption("OpenAI explanation: "+("key configured" if status["OpenAI key"] else "optional; not configured"))
        st.caption("Configuration is read from environment variables, .env or Streamlit secrets. Keys stay server-side.")

with st.sidebar.expander("Ranking preferences"):
    active_weights=st.session_state.get("ranking_weights",WEIGHTS)
    with st.form("ranking_preferences"):
        proposed={}
        for key,label in [("C","Complementarity"),("O","Funding relevance"),("R","Research relevance"),("E","Evidence quality")]:
            proposed[key]=st.number_input(label+" weight (%)",min_value=0,max_value=100,value=round(active_weights[key]*100),step=5)
        if st.form_submit_button("Apply ranking weights"):
            if sum(proposed.values())!=100:
                st.error("The four weights must add up to 100%.")
            else:
                st.session_state["ranking_weights"]={k:v/100 for k,v in proposed.items()}
                st.rerun()
    st.caption("Ranking preferences apply to this session. They do not represent success probabilities.")
active_weights=st.session_state.get("ranking_weights",WEIGHTS)
focus=repo.company(focus_id)
result=workflow(repo,focus_id,weights=active_weights)
recs=result["recommendations"]
st.markdown('<div class="kicker">INNOVATION INTELLIGENCE / '+html.escape(focus.name.upper())+'</div>',unsafe_allow_html=True)

def source_link(url,label="View source ↗"):
    st.link_button(label,url)

def evidence(cl):
    with st.expander(cl.category.replace("_"," ").title()+" · "+cl.classification+" · "+cl.verification_status):
        st.write(cl.text)
        if cl.excerpt: st.caption("Supporting excerpt: "+cl.excerpt)
        if cl.source_url: source_link(cl.source_url)
        st.caption("Retrieved "+(cl.retrieved_at or "not recorded")+" · "+cl.provenance+" · "+("fresh" if freshness(cl.retrieved_at) else "review freshness"))
        st.caption("Confidence reflects extraction/review, not independent company verification.")

def rec_card(rec,key,compact=False):
    with st.container(border=True):
        left,right=st.columns([5,1])
        with left:
            st.caption("HYPOTHESIS · "+str(len(rec["companies"]))+" COMPANY COMBINATION")
            st.subheader(rec["title"])
            st.write(" + ".join(rec["names"]))
        with right:
            st.metric("Match score",f"{rec['score']:.1f}")
        st.write(rec["problem"])
        st.caption(" · ".join(rec["shared_domains"]).upper()+" · Component coverage "+str(rec["coverage"])+"%")
        st.caption("Ranking weights: "+", ".join(k+" "+str(round(v*100))+"%" for k,v in rec.get("weights",WEIGHTS).items()))
        cols=st.columns(4)
        for col,(name,k) in zip(cols,[("Complementarity","C"),("Funding relevance","O"),("Research relevance","R"),("Evidence quality","E")]):
            val=rec["scores"][k]
            col.metric(name,"Missing" if val is None else f"{val:.0f}/100")
        if not compact:
            with st.expander("Why this combination?"):
                for e in rec["relationships"]:
                    st.write("**"+e["left"].replace("_"," ")+" + "+e["right"].replace("_"," ")+"** — "+e["why"])
                st.write("Missing capabilities: "+(", ".join(rec["missing"]) or "None in this concept taxonomy; validate implementation capacity."))
                st.warning("Unvalidated hypothesis. No company commitment, partnership or funding eligibility is implied.")
        if st.button("Open innovation blueprint →",key=key):
            st.session_state["selected_rec"]=rec["id"]
            st.session_state["open_blueprint"]=True
            st.rerun()

# A direct action opens the blueprint without relying on inaccessible multipage links.
if st.session_state.pop("open_blueprint",False):
    st.session_state["blueprint_override"]=True
if st.session_state.get("blueprint_override"):
    if st.button("← Return to workspace"):
        st.session_state["blueprint_override"]=False
        st.rerun()
    page="Innovation Blueprint"

if page=="Innovation Overview":
    st.title("Discover what comes next.")
    st.markdown('<div class="hero"><div class="kicker">FROM CAPABILITIES TO POSSIBILITIES</div><h2>Better together. Backed by evidence.</h2><p>Connect complementary companies to research, funding and practical first experiments. Every proposed innovation begins as a hypothesis you can inspect.</p></div>',unsafe_allow_html=True)
    metrics=st.columns(5)
    values=[len(companies),len({(c.id,cl.category) for c in companies for cl in c.claims if cl.supported() and cl.category!="membership"}),sum(r.kind=="research" for r in records),sum(r.kind=="funding" and r.status()=="open" for r in records),len(recs)]
    for col,label,value in zip(metrics,["Profiled companies","Sourced capabilities","Research records","Open funding records","Ranked hypotheses"],values):
        col.metric(label,value)
    st.caption("Counts come from stored public records and the current company's computed hypotheses. Sourced means checked against a public page, not independently audited.")
    col1,col2=st.columns([2,1],gap="large")
    with col1:
        st.subheader("Connections worth exploring")
        for rec in recs[:3]:
            rec_card(rec,"overview:"+rec["id"],compact=True)
        if not recs: st.info("No supported combination found. Review sourced capabilities and public domains.")
    with col2:
        st.subheader("Your company perspective")
        st.write("**"+focus.name+"**")
        st.write(focus.description)
        st.caption("PUBLIC CAPABILITY AREAS")
        st.markdown(" ".join('<span class="chip">'+html.escape(c.replace("_"," "))+'</span>' for c in focus.capabilities()),unsafe_allow_html=True)
        st.divider()
        st.subheader("Evidence before enthusiasm")
        st.write("1. Review company DNA.\n2. Refine public priorities.\n3. Inspect complementary connections.\n4. Export a testable blueprint.")
        st.divider()
        st.caption("RECENT SOURCE ACTIVITY")
        for log in repo.logs()[:4]:
            st.write(log["status"]+" · "+log["source"])
            st.caption(log["created_at"]+" · "+log["detail"])
    st.subheader("Ask for an innovation connection")
    with st.form("request"):
        query=st.text_input("Discovery request",placeholder="Find potential collaborators for a marine environmental monitoring project.")
        fetch_live=st.checkbox("Refresh research and funding before ranking",value=False,disabled=not ALLOW_LIVE,help="Sends the public discovery request to OpenAlex and retrieves Vinnova calls. Existing records remain available if a source fails.")
        submit=st.form_submit_button("Discover connections",type="primary")
    if submit:
        with st.spinner("Discovering evidence-backed connections"):
            answer=workflow(repo,focus_id,query,weights=active_weights,live=fetch_live and ALLOW_LIVE,public_demo=PUBLIC_DEMO)
        if answer["refresh"]:
            st.session_state["api_results"]=answer["refresh"]
            st.json(answer["refresh"])
        if answer["boundary"]["status"]=="supported":
            st.success(answer["boundary"]["message"])
            ranked=sorted(answer["recommendations"],key=lambda r:-(r["score"]+0.15*relevance(type("Q",(),{"title":r["title"],"description":r["problem"],"tags":r["capabilities"]})(),query,focus.capabilities())))
            for rec in ranked[:2]: rec_card(rec,"query:"+rec["id"])
        else: st.info(answer["boundary"]["message"])

elif page=="Member Directory":
    st.title("Member and partner directory")
    st.caption("Source-linked organisations from the supplied audit and the expanded public listing. Individual membership classes are not disclosed. This is not a complete ecosystem census.")
    directory_companies=[c for c in companies if c.directory_profile]
    search=st.text_input("Search organisations, industries and Swedish descriptions")
    cities=sorted({city for c in directory_companies for city in c.directory_profile.get('locations',[])})
    places=st.multiselect("Published locations",cities)
    local_only=st.checkbox("Show organisations with a published Blekinge location",value=False)
    from nexus.regional import in_blekinge
    entries=[]
    for company in directory_companies:
        p=company.directory_profile
        if search and search.casefold() not in (company.name+' '+p.get('description_original_sv','')+' '+' '.join(p.get('industry_original_sv',[]))).casefold():continue
        if places and not set(places)&set(p.get('locations',[])):continue
        if local_only and not in_blekinge(p.get('locations',[])):continue
        entries.append({'Organisation':company.name,'Industry (source Swedish)':', '.join(p.get('industry_original_sv',[])),
                        'Locations (as published)':', '.join(p.get('locations',[])),'Employee band (as published)':p.get('employee_range') or 'Not published',
                        'Profile evidence':p['blue_science_park_profile_url'],'Verification':p.get('profile_fetch_status','unknown'),
                        'Last checked':p.get('last_verified_at',''),'Missing fields':', '.join(p.get('missing_fields',[])) or 'None recorded'})
    st.write(str(len(entries))+" organisations shown")
    st.dataframe(pd.DataFrame(entries),hide_index=True,width='stretch',column_config={'Profile evidence':st.column_config.LinkColumn('Profile evidence')})
    audit_path=ROOT/'docs/directory_audit.json'
    if audit_path.exists():
        with st.expander("Directory coverage and crawl audit"):
            st.json(json.loads(audit_path.read_text(encoding='utf-8')))
    st.caption("Select a company in the sidebar, then open Company DNA to inspect each field's evidence. Location values are source-reported places, not independently verified office addresses.")

elif page=="Company DNA":
    st.title("Company DNA")
    st.write("Evidence-backed capabilities. Human-refined direction.")
    st.subheader(focus.name)
    st.write(focus.description)
    st.caption("Profile provenance: "+focus.provenance+". User-supplied descriptions and domains require source review.")
    source_link(focus.website,"Company website")
    if focus.directory_profile:
        profile=focus.directory_profile
        st.info("Verification: "+profile.get('profile_fetch_status','unknown')+" · checked "+profile.get('last_verified_at','unknown'))
        if profile.get('latest_fetch_status')=='failed':st.warning('Latest profile retrieval failed. The earlier supplied audit is retained with its original date.')
        st.caption("Listed organisation; member-versus-partner class is not individually disclosed.")
        st.write("**Original Swedish description**")
        st.write(profile.get('description_original_sv') or 'Not published')
        source_link(profile['blue_science_park_profile_url'],'Official directory profile')
        st.caption("Missing fields: "+(', '.join(profile.get('missing_fields',[])) or 'None recorded')+". Fields are transcribed source claims, not an independent company registry audit.")
        with st.expander("Field-by-field source evidence"):
            st.dataframe(pd.DataFrame(metadata_rows(profile)),hide_index=True,width='stretch',column_config={'Evidence source':st.column_config.LinkColumn('Evidence source')})
            st.caption(profile['domain_mapping_note'])
    else:
        st.caption("Verification: no audited directory profile attached. Review the individual claims below.")
    tabs=st.tabs(["Sourced facts","Inferred interests","Refine profile","Website review"])
    with tabs[0]:
        st.caption("Public-source claims and reviewed evidence. Each claim shows its own provenance and retrieval date.")
        for cl in focus.claims:
            if cl.classification=="FACT": evidence(cl)
        if not PUBLIC_DEMO:
            with st.expander("Add reviewed capability evidence"):
                with st.form("manual_evidence"):
                    category=st.selectbox("Capability category",list(TAXONOMY))
                    statement=st.text_input("Evidence-backed capability statement",max_chars=600)
                    source=st.text_input("Supporting HTTPS source URL",max_chars=1000)
                    excerpt=st.text_area("Supporting excerpt",max_chars=2000)
                    checked=st.checkbox("I checked that this public source supports the statement.")
                    if st.form_submit_button("Save reviewed capability"):
                        try:
                            add_reviewed_capability(repo,focus_id,category,statement,source,excerpt,checked)
                            st.rerun()
                        except ValueError as exc:st.error(str(exc))
    with tabs[1]:
        inferred=[cl for cl in focus.claims if cl.classification=="INFERENCE"]
        for cl in inferred: evidence(cl)
        if not inferred: st.info("No machine-inferred interests stored. User refinements appear separately below.")
        st.write("**User-supplied public interests**")
        st.write(", ".join(focus.interests) or "No interests added.")
        st.write("**Public priority:** "+(focus.priority or "Not supplied."))
        st.caption("Interests influence ranking; they are never promoted to verified capabilities.")
    with tabs[2]:
        with st.form("profile"):
            st.caption("Demo edits are saved only for this browser session and reset when it ends." if PUBLIC_DEMO else "Edits are public within this local prototype. Do not enter confidential information.")
            priority=st.text_input("Public innovation priority",value=focus.priority,max_chars=500)
            interests=st.text_area("Interests (one per line)",value="\n".join(focus.interests),max_chars=2000)
            domains=st.multiselect("Application domains (user supplied)",["digital","marine","energy","environment"],default=focus.domains)
            if st.form_submit_button("Save profile & recalculate",type="primary"):
                updated=repo.company(focus_id)
                updated.priority=priority.strip()
                updated.interests=list(dict.fromkeys(x.strip() for x in interests.splitlines() if x.strip()))[:20]
                if not domains:
                    st.error("Select at least one application domain.")
                else:
                    updated.domains=domains
                    repo.save_company(updated,expected_revision=focus.revision)
                    st.session_state["profile_saved"]=True
                    st.rerun()
        if st.session_state.pop("profile_saved",False):
            st.success("Profile saved. Recommendations recalculated from the new revision.")
        st.caption("Current revision: "+str(focus.revision))
    with tabs[3]:
        st.caption("Extracted candidate claims require review before they can influence matching. Page text is untrusted data.")
        url=st.text_input("Allowlisted official HTTPS page",value=focus.website)
        if st.button("Retrieve public page",disabled=PUBLIC_DEMO) and not PUBLIC_DEMO:
            with st.spinner("Checking robots and retrieving public evidence…"):
                try:
                    retrieved=CompanySources(repo).retrieve(url)
                    st.session_state["pending:"+focus_id]=[cl.__dict__ for cl in retrieved["claims"]]
                except (IntegrationError,ValueError) as exc:
                    st.error(str(exc))
        pending=st.session_state.get("pending:"+focus_id,[])
        for i,c in enumerate(pending):
            st.write(c["category"]+": "+c["text"])
            st.caption("Evidence excerpt: "+c["excerpt"])
            if st.button("Confirm sourced claim",key="confirm:"+str(i)+focus_id):
                updated=repo.company(focus_id)
                cl=Claim(**c);cl.verification_status="source_reviewed"
                updated.claims.append(cl)
                repo.save_company(updated,expected_revision=updated.revision)
                st.session_state["pending:"+focus_id]=[p for j,p in enumerate(pending) if j!=i]
                st.rerun()
    if not PUBLIC_DEMO:
        st.divider()
        with st.expander("Register a company"):
            with st.form("register_company"):
                st.caption("New profiles start as user input, not verified public facts. Add reviewed evidence before capability matching.")
                company_name=st.text_input("Company name",max_chars=120)
                company_website=st.text_input("Company HTTPS website",max_chars=1000)
                company_description=st.text_area("Public company description",max_chars=3000)
                company_domains=st.multiselect("Initial application domains",["digital","marine","energy","environment"],default=["digital"])
                if st.form_submit_button("Create company profile"):
                    try:
                        created=register_company(repo,company_name,company_website,company_description,company_domains)
                        st.session_state["company_created"]=created.name
                        st.rerun()
                    except ValueError as exc:st.error(str(exc))
        if st.session_state.pop("company_created",None):
            st.success("Company registered. Select it in Company perspective to review its evidence.")

elif page=="Innovation Graph":
    st.title("The connections between possibilities.")
    st.write("Explore sourced capabilities and proposed innovation paths.")
    nodes,edges=graph_data(companies,records,recs,focus_id)
    st.markdown(" ".join('<span class="chip" style="color:'+color+'">'+kind.title()+'</span>' for kind,color in COLORS.items()),unsafe_allow_html=True)
    if importlib.util.find_spec("plotly") and importlib.util.find_spec("networkx"):
        renderer=st.selectbox("Graph renderer",["Interactive evidence graph","Plotly / NetworkX"])
    else:
        renderer="Interactive evidence graph"
    if renderer=="Plotly / NetworkX":
        st.plotly_chart(plotly_figure(nodes,edges),width="stretch")
    else:
        st.iframe(graph_html(nodes,edges),height=640,alt="Innovation evidence and hypothesis graph")
    st.caption("Solid capability links are public sourced claims. Complementary and collaboration links are algorithmic hypotheses.")
    with st.expander("Relationship explanations and source index"):
        st.dataframe(pd.DataFrame(edges),hide_index=True,width="stretch")
        for n in nodes:
            if n["url"]: st.markdown("["+n["label"].replace("[","").replace("]","")+"]("+n["url"]+")")

elif page=="Opportunity Radar":
    st.title("Opportunity radar")
    st.write("Research, funding and testing environments through your company's perspective.")
    a,b,c=st.columns([1,1,2])
    types=a.multiselect("Record types",["research","funding","testbed","programme"],default=["research","funding","testbed"])
    status=b.selectbox("Funding status",["All","open","closed","upcoming","unknown"])
    minimum=c.slider("Minimum relevance",0,100,0)
    query=focus.public_text()+" "+focus.priority+" "+" ".join(focus.interests)
    ranked=sorted([(relevance(r,query,focus.capabilities()+focus.domains),r) for r in records],key=lambda x:(-x[0],x[1].id))
    for rel,r in ranked:
        if r.kind not in types or rel<minimum or (r.kind=="funding" and status!="All" and not r.status().startswith(status)): continue
        with st.container(border=True):
            st.caption(r.kind.upper()+" · "+r.provenance+" · "+r.status())
            st.subheader(r.title)
            st.write(r.description)
            st.write(f"**Relevance {rel:.1f}/100** · "+(r.publication_date or "Publication date unavailable"))
            st.caption("Retrieved: "+r.retrieved_at+" · Deadline: "+(r.deadline or "not recorded"))
            if r.authors: st.caption("Authors: "+", ".join(r.authors))
            overlap=sorted(set(r.tags)&set(focus.capabilities()+focus.domains))
            st.write("**Why it matters:** Shared capability/domain signals: "+(", ".join(overlap) or "lexical topic overlap only")+". Relevance is a ranking heuristic.")
            if r.eligibility: st.warning(r.eligibility+" Eligibility remains unconfirmed.")
            source_link(r.source_url,"Review evidence & next action ↗")
    st.divider()
    with st.expander("Live API refresh",expanded=True):
        live_query=st.text_input("OpenAlex research query",value=(focus.priority or " ".join(focus.capabilities()+focus.domains)).replace("_"," ")[:250],max_chars=300)
        sources=st.multiselect("Public APIs",["OpenAlex","Vinnova"],default=["OpenAlex","Vinnova"])
        today=datetime.now(timezone.utc).date()
        since=st.date_input("Vinnova records updated since",value=today-timedelta(days=90),max_value=today)
        pages=st.number_input("Research pages (verified OpenAlex key required beyond page one)",min_value=1,max_value=3,value=1,disabled=PUBLIC_DEMO)
        force=st.checkbox("Bypass the 24-hour response cache",value=False,disabled=PUBLIC_DEMO)
        st.caption("API results retain their original retrieval time. Sources refresh independently; failed requests do not replace stored evidence.")
        if PUBLIC_DEMO:
            st.caption("Public refresh is enabled with one batch per minute." if ALLOW_LIVE else "Public refresh is disabled by the host.")
        if st.button("Refresh selected APIs",disabled=not ALLOW_LIVE) and ALLOW_LIVE:
            if not sources:
                st.error("Select at least one public API.")
            else:
                with st.spinner("Retrieving live public records"):
                    st.session_state["api_results"]=refresh_sources(repo,live_query,sources=sources,force=force,since=since.isoformat(),pages=int(pages),public_demo=PUBLIC_DEMO)
                st.rerun()
        for name,result in st.session_state.get("api_results",{}).items():
            label=name+" · "+result["status"]+" · "+str(result.get("records",0))+" records"
            if result["status"] in {"live","cached"}:
                st.success(label)
            elif result["status"] in {"empty","cooldown","disabled"}:
                st.info(label+": "+result["message"])
            else:
                st.warning(label+": "+result["message"])
            if result.get("retrieved_at"):
                st.caption("Source retrieval: "+result["retrieved_at"])


elif page=="Innovation Blueprint":
    st.title("Turn a connection into a first experiment.")
    st.write("A source-linked brief for a conversation, a prototype and a decision.")
    if not recs:
        st.info("No supported blueprint candidates. Review the company profile first.")
    else:
        identities=[r["id"] for r in recs]
        previous=st.session_state.get("selected_rec")
        chosen=st.selectbox("Select a proposed combination",identities,index=identities.index(previous) if previous in identities else 0,format_func=lambda rid:next(r["title"]+" · "+" + ".join(r["names"]) for r in recs if r["id"]==rid))
        selected=next(r for r in recs if r["id"]==chosen)
        report=generate(selected,companies)
        st.warning("HYPOTHESIS · Companies have not confirmed participation. Funding and testbed access are not guaranteed.")
        st.download_button("Download innovation blueprint · Markdown",report,file_name="NEXUS_Innovation_Blueprint.md",mime="text/markdown",type="primary")
        st.markdown(report)
        with st.expander("Optional AI explanation"):
            st.caption("Uses only computed relationships. API keys are read from the environment. Deterministic explanations work without credentials.")
            if st.button("Explain this combination",disabled=PUBLIC_DEMO) and not PUBLIC_DEMO:
                explanation=explain(selected)
                st.caption(explanation["mode"])
                st.write(explanation["text"])
        st.divider()
        with st.form("feedback"):
            st.subheader("Would this be worth exploring?")
            rating=st.slider("Relevance rating",1,5,3)
            comment=st.text_input("What would make this more useful?",max_chars=1000)
            if st.form_submit_button("Save feedback"):
                repo.feedback(focus_id,selected["id"],rating,comment)
                st.success("Feedback stored. No feedback is sent externally.")

elif page=="Evaluation & Quality":
    st.title("Trust you can inspect.")
    st.write("Actual record quality, reproducible algorithm checks and explicit limitations.")
    claims=[cl for co in companies for cl in co.claims if cl.category!="membership"]
    sourced=sum(cl.supported() for cl in claims)
    fresh=sum(freshness(cl.retrieved_at) for cl in claims)
    cols=st.columns(3)
    cols[0].metric("Profile evidence coverage",f"{100*sourced/max(1,len(claims)):.0f}%")
    cols[1].metric("Fresh company evidence",f"{100*fresh/max(1,len(claims)):.0f}%")
    cols[2].metric("Mean component coverage",f"{sum(r['coverage'] for r in recs)/max(1,len(recs)):.0f}%")
    st.caption("Evidence coverage counts reviewed capability claims; freshness uses 90 days for profiles. Funding becomes unknown after 30 days without refresh.")
    st.subheader("Similarity baseline vs. complementarity")
    st.dataframe(pd.DataFrame(baseline(focus,companies)),hide_index=True,width="stretch")
    evaluation=evaluate()
    st.info(evaluation["label_source"])
    st.write(f"Benchmark candidate set: {evaluation['candidate_count']} manually labelled synthetic pairs.")
    comparison=[]
    for method in ["complementarity","similarity"]:
        m=evaluation["metrics"][method]
        comparison.append({"Method":method,"Precision@5":m["precision_at_5"],"Recall@5":m["recall_at_5"]})
    st.dataframe(pd.DataFrame(comparison),hide_index=True,width="stretch")
    st.caption("Top-five set differentiation: "+str(evaluation["metrics"]["ranking_differentiation"])+". This small designed fixture cannot establish superiority on real users.")
    with st.expander("Inspect all benchmark labels and scores"):
        st.dataframe(pd.DataFrame(evaluation["rows"]),hide_index=True,width="stretch")
    feedback=repo.feedback_rows()
    st.subheader("Human feedback")
    if feedback:
        st.write(f"{len(feedback)} locally submitted ratings · mean "+str(round(sum(f["rating"] for f in feedback)/len(feedback),2))+"/5")
        st.dataframe(pd.DataFrame(feedback),hide_index=True)
    else: st.info("No human relevance ratings collected. No time-saving or usefulness improvement claimed.")
    st.subheader("Executed validation")
    report_path=ROOT/"docs"/"validation_results.json"
    if report_path.exists(): st.json(json.loads(report_path.read_text(encoding="utf-8")))
    else: st.info("Run python scripts/validate.py to generate the validation report.")
    for filename,label in [("ui_test_results.json","Script-level UI execution"),("live_integration_results.json","Actual live integration attempts")]:
        path=ROOT/"docs"/filename
        if path.exists():
            with st.expander(label):
                st.json(json.loads(path.read_text(encoding="utf-8")))
    st.subheader("Retrieval health")
    st.dataframe(pd.DataFrame(repo.logs()),hide_index=True,width="stretch")
    st.subheader("Known limitations")
    st.write("- Local single-user prototype; authenticated multi-company hosting is not implemented.\n- Public capabilities are company self-reports, not independent technical audits.\n- Current runtime cannot resolve external hosts; live API success is unverified.\n- TF-IDF is the active fallback; sentence model requires optional installation and local model files.\n- SQLAlchemy, Pydantic, Plotly and NetworkX require optional packages in this runtime.\n- Synthetic evaluation is developer-authored; no independent relevance study or customer interviews.\n- Call conditions, funding eligibility, company commitment and testbed availability require human review.")
    st.caption("Workflow modules: public company ingestion → research and opportunity connectors → deterministic combination and ranking → evidence verification → blueprint. No autonomous outreach.")

