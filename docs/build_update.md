# Build update

## Implemented improvements

- Company registration in local Company DNA. New descriptions are explicitly USER_INPUT and cannot create verified capabilities by themselves.
- Manual capability evidence review with source URL, supporting excerpt, confirmation and duplicate-claim rejection.
- Profile provenance display and separate user-supplied application domains.
- Session-specific C/O/R/E ranking preferences, validated to total 100%.
- Applied weights are retained on each recommendation and included in its Markdown export.
- Empty, non-finite and negative ranking weights are rejected.
- Launch_NEXUS.bat checks required imports and starts the local Streamlit app.
- GitHub Actions configuration runs core and normal Streamlit tests when it is eventually published. That hosted CI configuration has not run yet.

## Verification

Read validation_results.json for the executed core suite. ui_test_results.json and public_demo_ui_results.json document the socket-free adapter and its limits. The local UI flow now covers profile refinement, changing ranking weights, registering a synthetic company and saving reviewed evidence. Synthetic UI data is written only to a disposable test database excluded from the package.

## Deployment status

This update is local and packaged for download. The GitHub repository currently contains the initial .gitignore only. The full public source upload remains paused pending explicit public-sharing approval; a request to build locally is not treated as that approval.

The runtime still lacks the optional neural/graph/database dependencies and live external API verification described in known_limitations.md. No completed production deployment or independent user study is claimed.

