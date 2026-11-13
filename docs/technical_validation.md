# Technical validation

Run scripts/validate.py for deterministic core checks, scripts/smoke_ui.py for UI execution and scripts/live_check.py for real network attempts. Machine-readable files in this folder record exact results and timestamps.

## Executed scope

- Core tests: persistent profile updates/reopening; revision conflicts; evidence classification and URLs; missing evidence; similarity and complementary matching; connected triples; weighted ranking; profile differentiation and priority sensitivity; funding expiry; blueprint sources/export; malicious-source treatment; relevant/unrelated/injection requests; private tenant access and end-to-end discovery.
- 71 tests cover the core plus HTTP schema parsing, anonymous and authenticated pagination, key redaction, original cache timestamps, retry bounds, partial failure, public refresh controls and updated ranking using mocked responses. The UI refresh button is also tested with mocked HTTP; it persists both record types.
- Real Vinnova retrieval returned 219 funding calls. The OpenAlex connector stored five real publications. Ranking with the imported API data completed in 0.34 seconds for the four-company local dataset; this is one measurement, not a scale benchmark. The latest production-connector results and failures are in live_integration_results.json. Company-site retrieval timed out. No actual OpenAI request was made.
- Python source compilation was executed.
- Normal Streamlit server/AppTest initialization was attempted. Windows socket access restrictions blocked asyncio's socketpair handshake.
- Script-level UI testing uses a clearly labelled test-only loop adapter. It does not establish live server or visual correctness; see ui_test_results.json.

No API-key-backed LLM call, neural sentence model, Plotly/NetworkX renderer or SQLAlchemy backend was executed because those optional dependencies/credentials were unavailable. Existing NEXUS_Source.zip could not be downloaded; the source archive remains untouched.

## Before a live presentation

Install core dependencies on a network-enabled laptop, run normal AppTest and a browser walkthrough, check the graph's JavaScript interactions, refresh source records, verify the current funding status, and confirm the optional packages separately if demonstrating them. Keep snapshots for a network outage. Do not replace logs with invented success.

