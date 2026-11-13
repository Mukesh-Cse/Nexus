# Known limitations

- This is an implemented local MVP, not completion of every item in the original broad prompt.
- Existing NEXUS_Source.zip was not modified: archive transfer failed in the restricted environment.
- Core code and deterministic tests execute. A normal Streamlit server/browser run could not complete because Windows denied the socket handshake used by asyncio. Script-level UI checks with the test adapter are separately reported.
- Vinnova returned 219 real calls. The OpenAlex connector imported five real publications; exact results are in live_integration_results.json. Company-site retrieval timed out. External sources can still fail or throttle requests.
- Four public company profiles and five opportunity records are a small sample. Company claims are sourced self-reports and require review; application domains are analyst assumptions or user refinements.
- Exact publication days were not captured for the research snapshots. Stored dates retain source precision, including a 2023 OpenAlex year for a Sensors paper whose volume is 2024; do not silently reinterpret it.
- No private company strategy, prior interaction history, credentials or real private profile data is included.
- No multi-user authentication or trusted tenant-context issuer exists. The private API guards are unit-tested but are not an authenticated deployment.
- TF-IDF cosine is the active tested fallback. A cached Sentence Transformers model and the optional Plotly/NetworkX, SQLAlchemy and Pydantic paths need installation and separate validation.
- The embedding implementation does not batch neural vectors and the graph is rebuilt on reruns. Bounded generation can miss valuable combinations.
- The taxonomy and proposal templates are deliberately small. They encode plausible capability dependencies, not proof that companies can or want to integrate.
- Website extraction is deliberately conservative: pending review, robots allowed, reviewed hosts, no redirects. Sites with dynamic content or restrictive robots will not import. Production ingestion needs egress isolation against DNS rebinding as well as the current checks.
- Closed funding is excluded from current bridges; unknown/stale calls can remain as downweighted context. Full eligibility is never automatically checked.
- The optional OpenAI explanation is not live-tested without account credentials. Structured JSON validation and safe deterministic fallback are tested with mocked HTTP; Pydantic adds validation when installed.
- No controlled user study, independent human labels, interviews, market validation or measured time savings. Synthetic benchmark metrics are not generalisable performance claims.
- Graph JavaScript interactions, screenshots, responsive rendering and browser download behavior remain to be verified in a real browser.
- Markdown export is implemented; PDF is not. The prompt permits PDF or Markdown.
- Scheduled source refresh, PostgreSQL/pgvector, FastAPI/React and distributed deployment are documented next steps, not implemented features.

