# API Contract: Invoice Intake and Review

Proposed contract; implementation will publish the authoritative OpenAPI schema and generate a TypeScript client. All routes are under `/api/v1/workspaces/{workspace_id}` unless otherwise noted. IDs are opaque. Every request requires an authenticated session and workspace membership; each mutation also requires a session-bound CSRF token. Operators can create/edit; reviewers can confirm/reject; administrators manage policies and mappings when authorized. Roles do not imply each other. No route exists for invoice approval, payment, or payment-instruction changes.

## Common conventions

- JSON responses use typed dates, decimal amounts encoded as strings and ISO currency codes. File uploads use multipart with strict request/file limits and content validation.
- Every mutable draft, workbook, mapping and policy has a version; changes use an expected version and return `409` on mismatch. Errors use `{code, message, details?, request_id}` and never leak another workspace's resource existence. `401` means unauthenticated, `403` unauthorized, `404` absent or inaccessible, `409` conflict, `413` size limit, `415` unsupported type, `422` invalid content, and `503` dependency unavailable.
- Untrusted field results contain `{value, state, uncertainty, evidence}`; evidence is `{page, location?}` or an explicit unavailable reason. A validation result has `type`, `status`, `reason`, evidence and relevant duplicate references/calculation. Status is `pass`, `warning`, `inconclusive`, or `hard_stop`.
- Authorization, body and file limits, scan/sandbox outcomes and audit failures are enforced server-side. A model or chat response cannot invoke a confirmation endpoint.

## Endpoints

| Method and path | Purpose and contract |
| --- | --- |
| `POST /documents` | Upload a PDF/JPEG/PNG/HEIC document. Returns `202` with document ID and processing status; failures identify unsupported content or limits. |
| `GET /documents/{id}` | Return document status, detected type, page count and per-page processing errors. |
| `GET /documents/{id}/pages/{page}/preview` | Stream an authorized, safe preview; never expose the original without the appropriate access check. |
| `POST /documents/{id}/drafts` | Start extraction for a document; returns a draft ID and processing status. Idempotent retry behavior must be documented in OpenAPI. |
| `GET /drafts/{id}` | Return draft version, editable fields/evidence, processing state, selected target, validation revision and current warnings. |
| `PATCH /drafts/{id}` | Accept expected draft version and validated field corrections/target changes; increments version, audits edits and invalidates affected checks and prior confirmation. |
| `POST /drafts/{id}/messages` | Accept an invoice question or requested correction; return labeled model-generated response and proposed edits. Application validates edits; no automatic record. |
| `POST /drafts/{id}/validate` | Run deterministic required-field, totals, duplicates, and mapping checks against supplied expected draft and current policy/target versions; return run ID and results including inconclusive outcomes. |
| `GET /drafts` | Paginated workspace-scoped history with search and status filters; access according to role and policy. |
| `POST /workbooks` | Upload a supported workbook snapshot or request a new workbook with name/layout. Returns logical workbook ID, version, worksheets and inspection results. |
| `GET /workbooks/{id}` | Return current version, worksheet/header details and support warnings. |
| `POST /workbooks/{id}/mappings` | Save or update a workspace-scoped worksheet/header-to-field mapping with expected workbook version and required customer columns. |
| `GET /workbooks/{id}/versions/{version}/download` | Download an authorized, committed workbook snapshot. Uploaded local source files are not remotely overwritten. |
| `POST /drafts/{id}/record` | Reviewer-only explicit confirmation; request and behavior below. Never called by the model or implicit chat flow. |
| `POST /drafts/{id}/reject` | Reviewer rejects with expected draft version and optional reason; audits decision and writes no workbook row. |
| `GET /drafts/{id}/audit` | Return authorized review, correction, validation and publication history, excluding secrets. |
| `GET/PUT /policy` | Authorized administrators view/change versioned rules. Policy updates invalidate affected validation/review. |

## Record request and response

`POST /drafts/{id}/record` accepts `Idempotency-Key` plus `{draft_version, validation_run_id, policy_version, workbook_id, workbook_version, mapping_version, warning_acknowledgements: [{warning_id, reason}]}`. The request is an explicit human action and means **record only**, not approve or pay.

The backend authenticates and authorizes the reviewer, confirms the supplied versions and acknowledgement/reasons, checks hard stops, coordinates workspace duplicate checks and workbook writes, then performs fresh validation against the authoritative latest workbook and workspace records. Any material change in reviewed warnings, policy, mapping, draft, target, or duplicate candidates rejects with `409` and requires renewed human review; a hard stop returns `422`. It stages an immutable candidate and atomically commits publication pointer, record reference, intent and audit. On success return `200` or `201` with `{status: "recorded", workbook_id, workbook_version, worksheet, row_or_reference, audit_id}`. For a pending recoverable operation return `202` and an intent reference; never indicate recorded before commit. A retry of the same idempotency key and fingerprint returns the same outcome; reuse with different content is `409`.

If publication fails or outcome is uncertain, keep the draft and intent, reconcile by candidate key/hash, and do not blindly append. Revalidate and obtain a new human decision if reviewed versions or warnings changed. See [data-model.md](../data-model.md).

## UI contract

The UI presents an accessible document preview, editable fields with source and uncertainty, check reasons and duplicate references, destination and mapping, and a dedicated review screen. It shows all unresolved warnings and required override reasons before the explicit record action. It clearly labels `recorded` as a log entry, not approval. It uses accessible status and error messages, keyboard navigation and no secret or sensitive invoice caching in local storage.
