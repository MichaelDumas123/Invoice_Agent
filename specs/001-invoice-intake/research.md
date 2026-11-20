# Phase 0 Research: Invoice Intake and Review

Research date: 2026-11-18. Decisions below are planning baselines, not evidence that implementation or production acceptance exists.

## Model and orchestration

- **Decision**: Use a direct LangChain model call for structured extraction and chat; no autonomous tool loop is required. Keep all authorization, validation and writes in deterministic backend services. Configure OpenRouter `qwen/qwen3.7-flash`; never silently switch providers/models. Render PDF pages and decode HEIC locally; evaluate Tesseract as a local OCR fallback.
- **Rationale**: The model proposes data but cannot enforce human approval, isolation or write integrity. OpenRouter currently lists this exact ID and image input, but its endpoint advertises `response_format` and does not advertise `structured_outputs`; validate all returned data and evidence independently. No authenticated inference was performed. OCR remains separately evaluated; external OCR requires its own data-processing approval.
- **Alternatives considered**: Autonomous Deep Agents (unnecessary reasoning/tool loop and elevated attack surface); cloud document OCR (requires separate vendor and privacy approval); replacing the configured model silently (prohibited).
- **Sources**: [OpenRouter model](https://openrouter.ai/api/v1/model/qwen/qwen3.7-flash), [structured outputs](https://openrouter.ai/docs/guides/features/structured-outputs), [LangChain OpenRouter](https://docs.langchain.com/oss/python/integrations/chat/openrouter), [Tesseract](https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html).
- **Release gate**: Verify actual account-specific model/endpoint availability, structured response behavior, image handling, costs and quality using synthetic and consented evaluation sets. Approve OpenRouter and each routed upstream provider's location, retention, subprocessors and terms; restrict routing and fail closed when unavailable. OpenRouter currently lists no EU in-region route for this model. Do not send invoice data before approval.

## Spreadsheet integrity

- **Decision**: Support application-managed immutable workbook snapshots initially; import uploaded `.xlsx` files as snapshots and provide updated downloads. Use `openpyxl` with a conservative, tested workbook-feature allowlist; reject unknown or unsafe features before modification, retain originals, and store invoice text as explicit string cells.
- **Rationale**: `openpyxl` documents potential loss of shapes, does not calculate formulas and does not enforce workbook validations. Table ranges, formulas and unsupported parts require explicit fidelity testing. A local upload cannot reveal later edits to the original on a user's computer.
- **Alternatives considered**: Arbitrary workbook round-tripping (cannot guarantee preservation); direct cloud/shared-drive editing (deferred until conditional publication and recovery are proven); CSV export (separate formula-injection risks).
- **Sources**: [openpyxl tutorial](https://openpyxl.readthedocs.io/en/stable/tutorial.html), [editing worksheets](https://openpyxl.readthedocs.io/en/stable/editing_worksheets.html), [security](https://openpyxl.readthedocs.io/en/stable/index.html).

## Recording concurrency and recovery

- **Decision**: Store versioned files in private object storage; keep authoritative current-version pointers in PostgreSQL. Bind an authenticated confirmation and unique workspace-scoped idempotency key to the exact draft, warnings, policy, mapping and workbook version. Serialize application writers per workbook, recheck duplicate candidates including other workspace records, stage an immutable candidate, then atomically compare-and-swap the pointer and commit the recorded result and audit event in a database transaction. Verify/reconcile staged objects on uncertain outcomes.
- **Rationale**: Object storage and a database do not share a transaction. Immutable staging plus a transactional pointer prevents an uncommitted candidate from being published and enables recovery; a shared lock around fresh duplicate checks prevents two different target workbooks in a workspace from independently passing the same duplicate check. Retry returns the previously committed outcome and a mismatched idempotency payload fails.
- **Alternatives considered**: In-process mutex or hash-check followed by overwriting a file (cannot protect multiple workers or external writers); distributed exactly-once claims (not supportable for unmanaged copies).
- **Scope limit**: Application-managed current versions only. A downloaded copy may diverge, and external edits to the original upload cannot be detected. Shared storage needs an independently proven conditional-write adapter.

## Identity, storage and uploads

- **Decision**: A same-origin React/TypeScript SPA and FastAPI backend use an approved organizational OIDC provider, server-side session with secure HttpOnly cookie and CSRF protection. PostgreSQL stores workspace, draft, audit and workflow data; private encrypted object storage keeps documents and immutable workbooks. Membership and role checks apply to every request; row-level security is defense in depth.
- **Rationale**: Server-enforced authorization and strong workspace isolation are required for sensitive invoices; browser-only role checks or mutable process-level request state are unsafe.
- **Alternatives considered**: Browser-held provider secrets/tokens (unacceptable exposure); local-only file state (inadequate audit and concurrency); external identity product hard-coded into the design (deployment choice unapproved).
- **Sources**: [OWASP CSRF](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html), [PostgreSQL row security](https://www.postgresql.org/docs/current/ddl-rowsecurity.html).
- **Decision**: Quarantine uploads, check actual content, enforce configurable byte/page/pixel/archive/decompression/time limits, scan for malware, and process hostile files in a resource-restricted non-root sandbox. Provide safe, authorized page previews.
- **Rationale**: Filename/MIME and ordinary upload spooling are not security controls. PDF, image and workbook parsers handle untrusted content.
- **Alternatives considered**: Direct browser previews or unbounded parser execution (unsafe). [OWASP upload guidance](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html).

## Versions, frontend and testing

- **Decision**: Target Python 3.12+, TypeScript 5.x, supported current React and FastAPI/Pydantic versions, with versions locked after compatibility testing. Use Vite for SPA tooling, pytest/HTTPX for backend tests, Vitest and Playwright for frontend/browser tests. A durable worker handles conversion and model calls; choose its concrete queue after deployment requirements are confirmed.
- **Rationale**: Stable mainstream tooling fits the required stack and enables unit, integration, accessibility and failure-injection tests. React guidance favors parallel independent reads, lazy loading heavy previews, derived state and event-based mutation; never trade away authorization, confirmation or durable audit for latency.
- **Alternatives considered**: Next.js SSR (not required by the product); process-only background tasks (not durable); unpinned latest versions (reproducibility risk).

## Deployment decisions and release approvals

Planning defaults above resolve architectural choices; organizational policy values are **release gates**, not fabricated approvals: identity provider/MFA, permitted hosting regions, retention/deletion, backups, limits and SLOs; workspace-specific required fields, duplicate rules, currency rounding/tolerances and hard stops; supported workbook-feature matrix; provider contracts; and representative evaluation datasets and thresholds. Production must not launch before their responsible owners approve them. No real invoice data should be used for development without authorization.
