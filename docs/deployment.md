# Render deployment handover

## Current status

The live preview is https://nexus-646z.onrender.com/ . Render service srv-dbrgl2bm8hqs73d08ph0 uses the Dockerfile. The initial four-company deployment from commit 67dc089a5bbca199381fc5beea7793394c3b104c was verified in a browser. The current source update adds 56 directory organisations and is verified by core and script-level UI tests before publication. Check the deployed directory page to verify this newer version after Render completes its build.

Source repository: https://github.com/Mukesh-Cse/Nexus . Public source publication was explicitly approved. The earlier missing-Dockerfile failure was resolved by publishing the complete app.

## Prepared configuration

- render.yaml provisions one Python web service on the Free compute plan in Frankfurt.
- .python-version requests Python 3.12 (latest supported patch).
- Build: python -m pip install -r requirements.txt.
- Start: python scripts/serve.py.
- Host: 0.0.0.0; port: platform PORT, default 10000.
- Health path: /_stcore/health.
- Auto deployment is off until explicitly enabled.
- No paid disk, database, API keys, outbound email or other paid resource is requested.

## Public demo data behavior

NEXUS_PUBLIC_DEMO=1 creates a separate in-memory SQLite repository inside each Streamlit session. Profile edits, recommendations and feedback remain scoped to that visitor. They survive reruns within that session but are lost when the session ends or the service restarts. The sourced baseline is restored for a new session.

Website imports and optional API-backed explanations are disabled in the anonymous demo UI. Public OpenAlex/Vinnova refresh is enabled by the supplied NEXUS_ALLOW_PUBLIC_REFRESH=1 setting; it allows one batch per minute per process, uses the response cache and limits research to one page. Set the flag to 0 to disable it. Public source links and snapshot-based research/funding bridges still work. Markdown exports remain available. This is a public demonstration, not authenticated company-private hosting.

Local mode keeps the existing disk-backed repository behavior. Use a paid persistent disk or a proper external database plus real authentication for a durable multi-user pilot; this handover does not provision either.

## Finish deployment

1. Push the prepared update to the already authorised Mukesh-Cse/Nexus repository.
2. Put the CONTENTS of NEXUS at the repository root so app.py, render.yaml and requirements.txt are at the root. Avoid committing .env, local databases or test caches.
3. Connect the repository to Render. Use New → Blueprint to read render.yaml, or New → Web Service with the exact build/start settings above.
4. Select the intended workspace, review the Free compute plan and create the service.
5. Watch the exact deployment to a terminal state. Check /_stcore/health and open the application.
6. In two separate browser sessions, edit a profile in one and verify the other retains the baseline.
7. Review all six pages and download a blueprint before sharing the URL.

A hosted URL will be available only after Render successfully deploys the service.

## Validation

Core unit tests include session isolation, feedback separation and the Render host/port command. Script-level UI checks cover local and hosted-demo modes with an explicitly documented socket-free test adapter. Real Render Blueprint CLI validation and hosted browser verification remain pending.

## Official references checked during preparation

- https://render.com/docs/blueprint-spec.md
- https://render.com/docs/web-services.md
- https://render.com/docs/python-version.md
- https://render.com/docs/free.md

These document the schema, public host/PORT requirement, .python-version selection and ephemeral filesystem limits. Bundled Render access references were unavailable; the deployment CLI was not installed, so no official CLI validation is claimed.

