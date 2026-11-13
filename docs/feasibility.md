# Feasibility and rollout

## Local demonstration

Four company profiles, five public opportunity records, deterministic matching and SQLite run without paid infrastructure or external API keys. The Python runtime used for core validation was 3.14.7 on Windows. Core requirements are separate from optional neural/graph/database extras.

## Pilot for 40+ members

Planning estimate, not a measured capacity guarantee: a small 2-vCPU/4-GB machine should be a reasonable starting point for this bounded workload, subject to load testing. A sentence model adds download size, startup time and memory; keep it out of the request path. Rate-limit external refresh, cache by source/query, persist record IDs and incrementally update profiles.

Candidate generation is bounded to 12 candidate partners and triples from 8. This keeps each focal search small but can miss useful combinations. TF-IDF fits many small pairwise vocabularies; precompute a shared vocabulary or vector store if latency grows. Streamlit reruns, synchronous retrieval, SQLite writer contention and public-page quality will dominate before large graph storage does.

A measured single focal search over 40 synthetic profile copies took 2.2801 seconds and returned 15 recommendations in this runtime. See scale_benchmark.json. This excludes retrieval, concurrent users and browser rendering and is not a production capacity claim.

## Rollout

1. Local supervised demonstration and normal browser QA.
2. Profile validation with willing members and independent recommendation labels.
3. Authenticated small pilot with real tenant authorization and isolated ingestion.
4. PostgreSQL, scheduled retrieval/review, observable freshness and operational monitoring.
5. Larger cohort only after measuring relevance, safety and response latency.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Missing/stale sources | Timestamped snapshots, freshness gates, visible refresh logs |
| Wrong capability extraction | Pending-review claims and company confirmation |
| Closed or unsuitable funding | Time-aware status, original source and eligibility caveats |
| Weak concept fit | Explicit gaps, evidence and independent review |
| Prompt injection | Deterministic parsing; external text has no tool authority |
| Website SSRF | Reviewed host allowlist and private-IP/redirect rejection; use isolated network egress for production |
| Private information leakage | Public-only demo, no confidential input, production auth required |
| Network outage | Honest offline mode and retained public snapshots |

## Open questions

Will companies review profiles? Which use cases deserve new taxonomy edges? How will ownership and permissions be verified? Which source terms allow routine refresh? What freshness cadence is sustainable? These require a partner pilot, not more architecture.

