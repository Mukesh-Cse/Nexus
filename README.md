# NEXUS — The Innovation Connection Engine

> Don't just discover opportunities. Discover what your company could become.

NEXUS is a local hackathon prototype for Blue Science Park. It connects public, evidence-backed company capabilities with complementary companies, research, funding and validation environments. Every collaboration proposal is explicitly a hypothesis.

## Hosted deployment

Live preview: https://nexus-646z.onrender.com/ . The existing Render service uses the included Dockerfile. The first four-company version was deployed and browser-checked; the directory update adds 56 source-linked organisations, field-level provenance and regional browsing. See docs/directory_verification_report.md and docs/directory_audit.json for the live crawl results.

Public mode uses isolated session memory: edits and feedback reset when the session ends. Local mode persists to SQLite. Company login and durable hosted tenant storage remain unfinished. Public API refresh is enabled with a one-minute process-level cooldown. No confidential company data should be entered.

## Start here — Windows PowerShell

Use Python 3.11 or newer. Python 3.12 is a practical choice for the optional ML packages.

```powershell
cd NEXUS
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open http://localhost:8501. After installing dependencies, Windows users can also double-click `Launch_NEXUS.bat`. If PowerShell activation is restricted, use `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` and `.\.venv\Scripts\python.exe -m streamlit run app.py` directly. You can also run `Start_NEXUS.ps1` after dependencies are installed.

The database is created and seeded automatically on first startup. No API keys or paid services are needed for the snapshot demonstration. The supplied public snapshot is a real source-reviewed dataset, not fictional companies or an API-response simulation.

**Validation:** 80 automated core/integration tests passed. Script-level UI checks are separately recorded. The initial hosted dashboard, radar, graph keyboard evidence inspection and blueprint content were browser-checked. The directory update has its own acceptance checks; no human usefulness or accuracy study is claimed.

## Features

New in this build: register a company in Company DNA, add source-reviewed capability evidence, and change the four ranking weights in the sidebar. User-supplied descriptions are labelled separately from sourced facts. Applied weights are included in exported blueprints.


- Seven views: Overview, Member Directory, Company DNA, Innovation Graph, Opportunity Radar, Innovation Blueprint, Evaluation & Quality.
- 56 source-linked directory organisations, preserving the original four reviewed capability profiles. Original Swedish text, individual field sources, missing fields, aliases and source history are retained. Wider ecosystem coverage is unknown.
- Claims retain source URL, excerpt, retrieval time, classification, confidence, review status and provenance.
- User-entered public priorities/interests persist separately from sourced capabilities; revisions invalidate stored recommendations.
- Bounded pair and triple candidate generation; explicit input/output and security dependencies distinguish complementarity from similarity.
- C/O/R/E score breakdown; missing components contribute zero with separate coverage.
- Research, funding and testbed bridges; time-aware funding status and freshness checks.
- Interactive source-linked graph with pan, zoom, node inspection and relationship filtering.
- Markdown blueprint export, feedback storage and synthetic benchmark inspection.
- Actual OpenAlex, Vinnova and robots-aware website connector implementations with timeouts, response limits, logs and caching.
- Code-level scope routing, privacy guards and untrusted-source handling.

## Architecture and implementation ownership

`app.py` is the Streamlit adapter. `nexus/service.py` orchestrates public profile, research, opportunity, combination, ranking and verification steps. These are explicit Python workflow stages, not independent autonomous agents or simulated LLM conversations. No LangGraph dependency is needed for this bounded workflow.

`nexus/core` contains UI-independent matching, scoring, blueprint, evaluation and graph logic. `nexus/integrations` handles external services. `nexus/database` owns versioned SQLite persistence, optionally using SQLAlchemy connection management. `nexus/security` owns application scope and private access guards.

Original application code, matching rules, data schema, source review, test fixtures, tests and documentation were implemented for this deliverable with AI assistance. Streamlit, NumPy, Pandas, scikit-learn, Requests and Beautiful Soup are reused libraries. Optional libraries are listed below. Public information comes from Blue Science Park, company websites, OpenAlex and Vinnova. No company partnership, endorsement, interview or commercial result is claimed.

## Configuration

Copy `.env.example` to `.env` for local settings. The app loads that file automatically, then reads whitelisted Streamlit secrets; existing environment variables take precedence. On Render, use service environment variables. See `docs/live_api_setup.md`.

```powershell
$env:OPENALEX_API_KEY = "your-optional-key"
$env:OPENAI_API_KEY = "your-optional-key"
$env:OPENAI_MODEL = "a-Responses-compatible-model"
```

Never commit credentials. API keys are not required for the default demonstration. Use a model available in your own account; the optional model integration was not live-tested here.

Install full optional dependencies only when needed:

```powershell
python -m pip install -r requirements-full.txt
```

- Plotly and NetworkX enable the second graph renderer. The default self-contained interactive graph works without them.
- SQLAlchemy enables managed SQLite connections; native sqlite3 is the tested offline fallback.
- Pydantic validates optional structured LLM explanation output. The deterministic domain layer uses validated dataclasses.
- Sentence Transformers can use a model already downloaded locally:

```powershell
$env:NEXUS_EMBEDDINGS = "sentence"
$env:NEXUS_EMBEDDING_MODEL = "C:\models\all-MiniLM-L6-v2"
```

Model loading is local-only; it never silently downloads a large model. Failure visibly falls back to TF-IDF cosine. The default and tested mode is TF-IDF. This baseline is lexical, not neural semantic understanding.

## External integrations and refresh

Use Opportunity Radar → Live API refresh → Refresh selected APIs, or:

```powershell
python scripts/live_check.py
```

OpenAlex: `https://api.openalex.org/works`, with a compact five-publication metadata page. Anonymous search retrieves the first page; a verified optional key enables cursor pagination bounded to three pages. Keys are sent in the Authorization header and are never logged. Publications retain titles, abstracts where available, authors, dates and canonical source IDs.

Vinnova: official public application-round API `https://data.vinnova.se/api/ansokningsomgangar/{updated-since-date}`. The UI defaults to records updated in the last 90 days, with an adjustable date. Up to 500 rounds are parsed per refresh; malformed records are logged. Swedish call dates use Europe/Stockholm. Missing dates remain unknown; eligibility is never confirmed automatically.

Both sources use a 24-hour persistent response cache that preserves the original retrieval time. The UI distinguishes live, cached, empty and unavailable results. Successful updates are persisted and used by ranking and blueprint evidence. A source failure retains existing records.

Company websites: only reviewed, allowlisted HTTPS hosts are accepted. DNS must resolve to public addresses. robots.txt must allow retrieval. Redirects and oversized pages are rejected. Extracted candidate claims stay pending until a user confirms the source supports them. Respect website terms in addition to robots.txt. Add reviewed hosts using `NEXUS_SOURCE_HOSTS`; this is a local administrator setting.

Actual network results are recorded in `docs/live_integration_results.json`. Vinnova returned 219 real call records in the verified run. The OpenAlex connector stored five real publications after switching to compact metadata and a longer bounded timeout. Company-site retrieval timed out. No successful OpenAI request is claimed; that optional explanation feature needs your own account key.

## Validation

```powershell
python scripts/validate.py
python scripts/smoke_ui.py
# Optional pytest runner:
python -m pytest -q
```

The unit/integration suite uses deterministic data and mocked HTTP. `docs/validation_results.json` records actual results and the 21-pair developer-authored synthetic benchmark. There are no human relevance ratings until a person submits them. No user study, statistical improvement or time-saving claim is supported.

The development environment disallowed the local socket handshake used by asyncio. A test-only synchronous loop identity adapter was therefore used:

```powershell
python scripts/smoke_ui.py --socket-free
```

This still executes the real Streamlit script and widget state changes, but does not test a running server, browser rendering, JavaScript graph behavior, async work or network I/O. Read `docs/ui_test_results.json` for the actual outcome. Use normal AppTest and browser validation on your own machine before the live demo.

## Data and privacy

The database is `data/nexus.sqlite3`, or the file configured in `NEXUS_DB`. Schema version 1 includes company/capability/evidence, research/funding/testbeds, opportunities, recommendations, hypotheses, revisions, feedback, private-note and retrieval-log tables, with indexes and foreign keys. Updates use optimistic revision checks.

Local mode is a single-user workspace. Hosted anonymous mode isolates browser sessions. Public profile refinements and feedback are shared inside the local workspace. Do not enter confidential data. The backend private-note API requires an authenticated tenant context; the UI does not provide private data access or login. Production authentication, authorization context issuance, tenant isolation and audit deployment remain unfinished.

## Demo

1. Select Baltic Offshore and review its public facts and sources.
2. Add a public priority such as “Trustworthy industrial data platform”.
3. Save and inspect recomputed scores.
4. Compare Cleura's first recommendation with Baltic Offshore's.
5. Inspect the interactive graph and an individual relationship.
6. Review funding dates and eligibility caveats in Opportunity Radar.
7. Export a Markdown blueprint and explain the first experiment.
8. Open Evaluation & Quality to show actual tests, source status and benchmark limits.

See `docs/demo_script.md` for the pitch and offline backup. The remaining documentation covers architecture, methodology, feasibility, user validation, traceability and known limitations.

## Roadmap

Validate capabilities and relevance with member companies first. For a pilot, add real authentication, restricted ingestion workers, scheduled review, independent benchmark labels and full browser QA. Then migrate repository storage to PostgreSQL/pgvector and expose the stable core through FastAPI with React if justified. Neo4j is optional only if graph query requirements outgrow the current bounded graph.

The archive is a separate implementation from Prompt.txt. Existing NEXUS_Source.zip could not be downloaded in this restricted runtime and was preserved without modification.


## Directory refresh

The supplied audited seed has 55 organisations and is retained unchanged. An expanded live listing reached 56 cards and no Load More control; all 56 profile pages were retrieved. This verifies the observed public listing, not the full wider ecosystem. DNV Cyber employee band remains unpublished. No individual member/partner classes are guessed.

Run `python scripts/crawl_blue_science_park.py --listing data/directory_listing_observation.json` to revisit the recorded URLs, or add `--retry-failed` to preserve successful fetches. For a NEW dynamic listing expansion, install optional Playwright, run `python -m playwright install chromium`, then `python scripts/crawl_blue_science_park.py --browser`. Optional browser dependencies are not required for the app. Both routes retain seed records and produce data/directory_snapshot.json and docs/directory_audit.json. Review changes before publishing a refreshed snapshot.

Use Member Directory to search organisations and filter published places or Blekinge locations. Company DNA displays verification status and exact field sources. Geographic preference currently breaks ties between equally scored partners; there is no live event or webinar ingestion in this build. Ymner and company login are separate future integrations.
