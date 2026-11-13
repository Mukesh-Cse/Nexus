# Architecture

## Implemented flow

Streamlit calls `workflow`, which routes requests to the public innovation scope, loads the current company revision, optionally refreshes external records, generates bounded pair/triple candidates, ranks evidence-backed hypotheses and persists validated results. A blueprint is generated only against matching company revisions.

| Stage | Module | Real behavior |
|---|---|---|
| Company intelligence | integrations/company_sources.py | Robots-aware page retrieval, taxonomy extraction, manual source review |
| Research intelligence | integrations/openalex.py | Cursor-based retrieval, author/date parsing and deduplication |
| Opportunity intelligence | integrations/vinnova.py | Documented application-round schema, timezone-aware dates |
| Combination | core/matching_engine.py | Shared applications and explicit capability dependencies |
| Ranking | core/scoring.py | Fixed initial weights, zero for missing components |
| Verification | models.py, service.py | Evidence requirements, reviewed-capability gate, hypothesis validation |
| Brief generation | core/blueprint_generator.py | Current-revision Markdown with evidence and next experiments |

These are connected workflow stages, not independently operating autonomous agents. Optional LLM output explains existing relationships and cannot change scores, create records or access private notes.

## Persistence

SQLite schema version 1, foreign keys and indexes. CompanyCapability links Company, Capability and Evidence. ResearchPublication, FundingOpportunity and Testbed specialise Opportunity. Recommendation references a company and contains a score breakdown. CollaborationHypothesis stores unvalidated candidates. CompanyProfileRevision preserves previous public states. UserFeedback stores explicit ratings; RetrievalLog captures external attempts. API responses are cached independently.

Native sqlite3 is the tested offline backend. An installed SQLAlchemy manages the underlying SQLite connection through the same repository; that optional path is not tested in this environment.

## Boundaries

Public profile data and private notes are separate. The UI exposes public-only operations. AuthContext must be issued by a trusted authentication layer in a real deployment; the prototype does not implement that layer. Local caller-supplied context is a unit-test construct, not production authentication.

Website hosts are allowlisted; private addresses and redirects are blocked. The content pipeline is deterministic and never executes webpage instructions. Optional LLM input receives only computed relationship strings, not webpage commands. Source stripping is defence in depth, not a universal prompt-injection classifier.

## Migration path

Maintain the Company/Record dataclass contracts and matching engine. Replace the SQLite repository with PostgreSQL tables and proper migration tooling, use pgvector for cached neural embeddings, and add tenancy in every query. FastAPI can expose workflow/profile/blueprint endpoints. React can replace the Streamlit adapter. Introduce background queues for isolated retrieval and scheduled review only after operational demand. Keep a relational evidence source of truth if Neo4j is later justified.

