# Live API setup

## Start and refresh

Install requirements.txt, then run `python -m streamlit run app.py`.
Open Opportunity Radar → Live API refresh. Enter a research query, select OpenAlex and/or Vinnova, choose the Vinnova update date, and click **Refresh selected APIs**.
Innovation Overview also has **Refresh research and funding before ranking** in its discovery form.

Successful records are stored in SQLite and become available to opportunity ranking and blueprint evidence. Results distinguish live, cached, empty and unavailable responses; a failed source leaves existing records available. The cache lasts 24 hours and displays the original retrieval timestamp, not the latest button-click time. Local users can bypass it explicitly.

## Credentials

Copy `.env.example` to `.env` at the project root for local configuration. Existing environment variables take precedence. The app also reads whitelisted Streamlit secrets. For Streamlit Cloud, enter settings in its Secrets editor; for Render, use service environment variables. `.streamlit/secrets.toml.example` shows the TOML structure. Real .env and secrets.toml files are excluded from Git and the packaged ZIP.

- **Vinnova:** no API key required. The update date defaults to 90 days ago. Up to 500 application rounds are parsed, with source URLs, deadlines and eligibility text. An updated record is not necessarily an open call; use the funding-status filter.
- **OpenAlex:** anonymous first-page search is supported. A verified `OPENALEX_API_KEY` enables cursor pagination: five works per page, up to three pages. Keys are sent in the Authorization header. Compact metadata includes available abstracts, authors, publication dates and canonical IDs.
- **OpenAI explanations:** optional `OPENAI_API_KEY` and `OPENAI_MODEL`. The local blueprint explanation button uses the Responses API with structured JSON. Matching remains deterministic. No key means the sourced deterministic explanation is used. This path was tested with mocked responses; no account-backed request was executed.

No credentials need to be entered into chat. Set keys only in local or hosting configuration.

## Public demo

`NEXUS_PUBLIC_DEMO=1` isolates each visitor's data in session memory. Set `NEXUS_ALLOW_PUBLIC_REFRESH=1` to enable public research/funding refresh (included in render.yaml). It permits one refresh batch per minute per server process and one research page, with cache bypass disabled. Set the flag to 0 to disable refresh. This is a small-demo safeguard, not distributed quota management. Website imports and optional paid explanations remain unavailable in anonymous mode.

## Verification

`python scripts/live_check.py` makes actual requests and records results in `docs/live_integration_results.json`. `python scripts/validate.py` tests parsing, caching, authentication handling, rate limits, partial failures and matching with mocked HTTP. `python scripts/smoke_ui.py` also tests the refresh button using mocked HTTP; the script-only adapter option does not test a running browser/server.

The verified Vinnova run imported 219 real call records. The OpenAlex connector also imported five real publications after selecting compact metadata and allowing a bounded 8-second connection / 25-second read timeout. Network response times varied between attempts; the latest results are recorded in the report. Company-website retrieval timed out. Authentication errors, source throttling and network failures are shown explicitly instead of being replaced with fictional data.
