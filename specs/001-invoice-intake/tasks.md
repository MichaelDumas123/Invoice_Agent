---

description: "Actionable implementation tasks for Invoice Intake and Review"
---

# Tasks: Invoice Intake and Review

**Input**: Design documents from `specs/001-invoice-intake/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/api.md`, and `quickstart.md`.

**Tests**: Included because the project constitution requires automated tests for extraction, validation, authorization, spreadsheet writes, and normal/invalid/ambiguous/failure behavior.

**Organization**: Tasks are grouped by user story. All paths below are relative to the repository root. Work is planned; none of the listed implementation files are presumed to exist yet.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish reproducible backend/frontend projects and local test services without enabling external invoice processing.

- [X] T001 Create the Python backend package structure and locked dependency manifest in `backend/pyproject.toml`, `backend/uv.lock`, and `backend/src/invoice_assistant/`.
- [X] T002 [P] Create the React/TypeScript Vite project, strict TypeScript configuration, and locked dependencies in `frontend/package.json`, `frontend/package-lock.json`, `frontend/tsconfig.json`, and `frontend/vite.config.ts`.
- [X] T003 [P] Add backend formatting, lint, and type-check configuration in `backend/pyproject.toml` and `backend/ruff.toml`.
- [X] T004 [P] Add frontend lint and format configuration in `frontend/eslint.config.js` and `frontend/.prettierrc.json`.
- [X] T005 Add local PostgreSQL and private object-store test services with health checks in `compose.yaml`.
- [X] T006 Add a secret-free environment-variable template and setup guidance in `.env.example` and `README.md`.
- [X] T007 Add synthetic invoice and workbook fixture directories with provenance/readme and no real invoice data in `backend/tests/fixtures/README.md`, `backend/tests/fixtures/invoices/`, and `backend/tests/fixtures/workbooks/`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement shared authorization, versioned persistence, safe processing primitives, and API contracts before user-story work.

**Checkpoint**: No user-story task begins until these cross-cutting controls and interfaces exist.

- [X] T008 Create database migrations for workspace, membership, policy version, document, page, draft, field, conversation, workbook/version, mapping, validation, review, record intent, recorded invoice, and audit entities in `backend/src/invoice_assistant/persistence/migrations/`.
- [X] T009 [P] Implement workspace-scoped identity, explicit operator/reviewer/administrator roles, and deny-by-default authorization dependencies in `backend/src/invoice_assistant/auth/`.
- [ ] T010 [P] Implement server-side OIDC session validation and role-independent reviewer authorization in `backend/src/invoice_assistant/auth/session.py` and `backend/src/invoice_assistant/auth/authorization.py`; only a fail-closed production placeholder exists, so OIDC integration remains open.
- [X] T011 [P] Implement development CSRF token and Origin validation for state-changing routes, including multipart requests, in `backend/src/invoice_assistant/api/csrf.py`; session binding remains gated on production OIDC integration.
- [X] T012 Implement database transaction context, workspace row-level security setup, and pooled-connection tenant-context reset in `backend/src/invoice_assistant/persistence/database.py` and `backend/src/invoice_assistant/persistence/tenant_context.py`.
- [X] T013 [P] Implement private object-storage access, encryption configuration, immutable object keys, and workspace-scoped object authorization in `backend/src/invoice_assistant/persistence/object_store.py`.
- [X] T014 Implement versioned workspace policies and defaults for required fields, duplicate rules, currency tolerance/rounding, hard stops, overrides, upload limits, and retention in `backend/src/invoice_assistant/domain/policy.py`.
- [X] T015 [P] Implement Pydantic request/response schemas for field state/evidence, validation status, pagination, version conflicts, and common errors in `backend/src/invoice_assistant/api/schemas.py`.
- [X] T016 Implement audit event persistence and redaction that excludes credentials and unnecessary invoice contents in `backend/src/invoice_assistant/domain/audit.py` and `backend/src/invoice_assistant/persistence/audit_repository.py`.
- [X] T017 Implement durable job enqueue/claim/retry interfaces and failure status persistence for document processing in `backend/src/invoice_assistant/workers/queue.py`.
- [X] T018 Implement FastAPI application factory, router registration, request IDs, response models, body limits, and standardized error responses in `backend/src/invoice_assistant/api/main.py` and `backend/src/invoice_assistant/api/errors.py`.
- [X] T019 [P] Generate and configure a TypeScript API client from FastAPI OpenAPI without hand-editing generated output in `frontend/src/services/generated/` and `frontend/package.json`.
- [X] T020 Implement frontend API request flows with CSRF headers and typed error handling, and no localStorage persistence in `frontend/src/App.tsx`.
- [X] T021 Add shared test identity, isolated workspace fixtures, fake object store, fake queue, and fake model provider in `backend/tests/conftest.py` and `frontend/tests/e2e/fixtures/`.
- [X] T022 Add foundational authorization tests for cross-workspace resource IDs, role separation, direct route invocation, CSRF failure, and pooled tenant-context reset in `backend/tests/integration/test_authorization.py`.

---

## Phase 3: User Story 1 - Prepare and review an invoice entry (Priority: P1) 🎯 MVP

**Goal**: An operator can safely upload an invoice, inspect and correct an evidence-linked extraction draft, and see review status. No unconfirmed draft can write a row.

**Independent Test**: With synthetic supported invoice fixtures and fake extraction, upload a document, verify per-page status and editable fields/evidence/uncertainty, correct a field and inspect its audit event, then prove no row is written without authorized confirmation.

### Tests for User Story 1

- [X] T023 [P] [US1] Add document upload contract tests for PDF/JPEG/PNG/HEIC, unsupported type, malformed/encrypted file, size limit, and content-signature mismatch in `backend/tests/unit/test_document_intake.py`.
- [X] T024 [P] [US1] Add multipage PDF, image/HEIC conversion, page-limit, and document preview tests in `backend/tests/unit/test_document_conversion.py` and `backend/tests/test_document_status.py`.
- [X] T025 [P] [US1] Add extraction-schema tests for present, missing, unreadable, inferred, uncertain, and evidence-unavailable invoice fields in `backend/tests/unit/test_extraction_validation.py`.
- [X] T026 [P] [US1] Add API integration tests for operator upload, draft retrieval, correction auditing, version conflict, and no-confirmation/no-write behavior in `backend/tests/test_demo_api.py`.

### Implementation for User Story 1

- [X] T027 [P] [US1] Implement quarantined upload signature/type, byte-size, encrypted-PDF marker and safe error validation in `backend/src/invoice_assistant/documents/intake.py`; parsed page/pixel/decompression/time limits and malware scanning remain pending isolated processing.
- [X] T028 [P] [US1] Implement bounded PDF rendering and JPEG/PNG/HEIC/HEIF conversion with per-page statuses and safe re-encoded previews in `backend/src/invoice_assistant/documents/conversion.py` and `backend/src/invoice_assistant/api/routes.py`; process-level sandbox isolation remains open.
- [ ] T029 [US1] Implement sandbox worker limits, non-root execution configuration, no unrestricted network, malware scanning, and per-page processing error capture in `backend/src/invoice_assistant/workers/document_worker.py` and `backend/config/document-worker/`; secure isolated parsing remains a production blocker.
- [X] T030 [P] [US1] Implement configurable extraction provider protocol and deterministic fake provider; external model calls remain disabled unless provider approval is configured in `backend/src/invoice_assistant/documents/extraction_provider.py` and `backend/src/invoice_assistant/documents/fake_extractor.py`. OCR is not implemented.
- [X] T031 [US1] Implement the LangChain/OpenRouter adapter boundary for the configured `qwen/qwen3.7-flash` target with explicit fail-closed behavior; live image extraction remains disabled pending verified capability and provider approval in `backend/src/invoice_assistant/documents/openrouter_extractor.py`.
- [X] T032 [US1] Implement extraction response validation that rejects unknown fields, preserves missing/unreadable/inferred states and evidence references, and never treats model confidence as proof in `backend/src/invoice_assistant/documents/extraction_validation.py`.
- [X] T033 [US1] Implement document/draft state transitions and failed/retry statuses in `backend/src/invoice_assistant/domain/models.py`; durable persistence remains a production task.
- [X] T034 [US1] Implement workspace-authorized development-only upload, document status, safe rendered-preview response, draft creation/retrieval, and correction routes with expected-version checks in `backend/src/invoice_assistant/api/routes.py`; production upload remains disabled.
- [X] T035 [US1] Implement audited field correction and invalidate validation/review versions after each material edit in `backend/src/invoice_assistant/api/routes.py`.
- [X] T036 [US1] Build accessible upload/chat workspace with visible processing status and actionable errors in `frontend/src/App.tsx` and `frontend/src/styles.css`.
- [X] T037 [US1] Build safe preview-unavailable placeholder and editable extraction form showing missing/unreadable/not-extracted status in `frontend/src/App.tsx` and `frontend/src/styles.css`.
- [X] T038 [US1] Build chat interactions that label demo responses and submit no privileged actions in `frontend/src/App.tsx`.
- [X] T039 [US1] Add Playwright flows covering sample review, chat, keyboard-accessible controls, safe synthetic PDF preview without extraction, and no false write claim in `frontend/tests/e2e/invoice-review.spec.ts`; tests use an isolated backend port.
- [X] T040 [US1] Add documented smoke-test procedures for supported/unsupported uploads and draft recovery using synthetic fixtures in `backend/tests/integration/README.md`, `backend/tests/fixtures/README.md`, and `README.md`.

**Checkpoint**: P1 is independently demonstrable using the fake provider; no invoice row is written without the authorized recording flow.

---

## Phase 4: User Story 2 - Configure and record to an invoice log (Priority: P2)

**Goal**: An AP operator configures a custom `.xlsx` destination or new workbook, and an authorized reviewer records one row with safe conflict handling, idempotent recovery, and an auditable destination reference.

**Independent Test**: Import a supported synthetic workbook with custom headers, map fields, review a draft as a reviewer, confirm and verify one row and a downloadable immutable workbook version. Repeat the request and simulate conflicts/failures; no duplicate or lost update is allowed.

### Tests for User Story 2

- [X] T041 [P] [US2] Add workbook API tests for upload, mapping, download authorization, and workspace isolation in `backend/tests/test_workbook_api.py`.
- [X] T042 [P] [US2] Add workbook inspection/fidelity tests for supported feature allowlist, formulas, tables, merged cells, invalid/encrypted packages, ZIP limits, long text, and formula-like strings in `backend/tests/unit/test_workbook_adapter.py`.
- [X] T043 [P] [US2] Add recording protocol integration tests for stale versions, same idempotency key, changed fingerprint, and hard-stop no-write behavior in `backend/tests/test_recording_api.py`.
- [X] T044 [P] [US2] Add development recovery reporting test for pending record intents in `backend/tests/integration/test_record_recovery.py`; true storage/DB crash-failure injection remains open because the prototype adapters are in-memory.

### Implementation for User Story 2

- [X] T045 [P] [US2] Implement workbook upload validation and read-only inspection with an explicit OOXML feature allowlist; reject unknown features rather than silently round-trip them in `backend/src/invoice_assistant/workbooks/inspection.py`.
- [X] T046 [US2] Implement workbook adapter for worksheet/header inspection, mapped append, explicit string cells for untrusted text, and configured package/text limits in `backend/src/invoice_assistant/workbooks/xlsx_adapter.py`; advanced workbook fidelity remains constrained by the documented allowlist.
- [X] T047 [US2] Implement prototype workbook snapshot/version entities and immutable staging with hashes in `backend/src/invoice_assistant/workbooks/version_store.py`; durable object storage is still required for production.
- [X] T048 [US2] Implement new workbook creation, configurable naming/layout, and downloadable committed versions in `backend/src/invoice_assistant/workbooks/workbook_service.py`.
- [X] T049 [US2] Implement workspace-scoped header mappings and header-change detection in `backend/src/invoice_assistant/workbooks/mapping_service.py`.
- [X] T050 [US2] Implement in-process demo writer coordination and compare-and-swap publication in `backend/src/invoice_assistant/workbooks/publication_service.py`; durable cross-worker transaction publication remains open.
- [X] T051 [US2] Implement confirmation idempotency key uniqueness, request fingerprint comparison, pending intent recovery reporting, and orphan candidate reconciliation guidance in `backend/src/invoice_assistant/workbooks/record_intent_service.py` and `backend/src/invoice_assistant/workers/reconciliation_worker.py`; durable restart-safe recovery remains unimplemented.
- [X] T052 [US2] Implement explicit reviewer-only record-to-workbook route bound to draft, validation, mapping, and workbook versions; return conflicts for stale review and expose no approval/payment actions in `backend/src/invoice_assistant/api/routes.py`.
- [X] T053 [US2] Implement workbook upload/creation, worksheet/header preview, field mapping, and snapshot download controls in `frontend/src/App.tsx`.
- [X] T054 [US2] Implement reviewer confirmation controls with warning acknowledgement reasons, disabled-until-ready recording, and explicit log-only copy in `frontend/src/App.tsx`.
- [X] T055 [US2] Implement workspace history and workbook snapshot download UI with stable record references and log-only status text in `frontend/src/App.tsx`.
- [X] T056 [US2] Add backend integration coverage for custom headers, mapping, reviewer recording, one-row output, downloadable workbook in `backend/tests/test_recording_api.py`; frontend E2E coverage remains open.

**Checkpoint**: P2 supports application-managed snapshots only; uploaded original files are not live-linked, and shared-drive editing remains out of scope.

---

## Phase 5: User Story 3 - Identify exceptions and likely duplicates (Priority: P3)

**Goal**: Reviewers see evidence-based, deterministic warnings for required fields, totals, duplicate candidates, confidence/conflicts, and mapping; hard stops block and permitted overrides require an audited reason.

**Independent Test**: Run synthetic invoices through validation with sufficient, missing, and ambiguous inputs; verify pass/warning/inconclusive/hard-stop semantics, displayed evidence, post-edit revalidation, and enforced overrides.

### Tests for User Story 3

- [X] T057 [P] [US3] Add decimal/currency validation tests for tax, charges, discounts, configured tolerance, rounding boundaries, missing components and inconclusive outcomes in `backend/tests/unit/test_validation.py`.
- [X] T058 [P] [US3] Add duplicate matching tests for normalization, same/different vendor, invoice identifiers, amount/currency/date signals, missing identifiers, accessible scope and candidate rationale in `backend/tests/unit/test_validation.py`.
- [X] T059 [P] [US3] Add policy tests for required fields, hard-stop blocking, allowed override reason, reviewer identity, and policy-version invalidation in `backend/tests/unit/test_domain_models.py` and `backend/tests/unit/test_validation.py`.
- [X] T060 [P] [US3] Add API tests for warning status, hard-stop results, and inconclusive checks for unprocessed documents in `backend/tests/test_validation_api.py`.

### Implementation for User Story 3

- [X] T061 [P] [US3] Implement deterministic required-field and missing/unreadable PO validation using workspace policy in `backend/src/invoice_assistant/domain/validation.py`.
- [X] T062 [P] [US3] Implement decimal-safe total reconciliation with currency minor-unit rounding/tolerance and explicit inconclusive results for incomplete components in `backend/src/invoice_assistant/domain/validation.py`.
- [X] T063 [US3] Implement normalized duplicate candidate search across the selected current log and workspace application records, with rationale and references; return inconclusive for missing/ambiguous identifiers in `backend/src/invoice_assistant/domain/validation.py`.
- [X] T064 [US3] Implement version-bound validation runs that aggregate required-field, arithmetic, duplicate, extraction, and mapping outcomes in `backend/src/invoice_assistant/domain/validation.py` and `backend/src/invoice_assistant/api/routes.py`.
- [X] T065 [US3] Integrate fresh validation and duplicate/write coordination before publication; reject changed warning sets for renewed reviewer decision in `backend/src/invoice_assistant/workbooks/publication_service.py` and `backend/src/invoice_assistant/api/routes.py`.
- [X] T066 [US3] Implement policy-enforced hard stops, reasoned warning acknowledgements, and audit events in `backend/src/invoice_assistant/api/routes.py` and `backend/src/invoice_assistant/domain/audit_service.py`; durable audit storage remains unimplemented.
- [X] T067 [US3] Implement validation endpoint and paginated history/audit responses scoped to workspace in `backend/src/invoice_assistant/api/routes.py`.
- [X] T068 [US3] Build accessible validation panel showing calculations, inconclusive reasons, duplicate references, missing PO warnings in `frontend/src/App.tsx` and `frontend/src/styles.css`.
- [ ] T069 [US3] Add Playwright tests verifying warning rationale, hard-stop block, allowed override reason, and clear non-approval semantics after an extracted draft in `frontend/tests/e2e/exception-review.spec.ts`; extraction is unavailable so production exception-flow E2E remains gated.

**Checkpoint**: All checks are application-owned; missing evidence cannot become a pass, and no warning override weakens the no-approval/no-payment boundary.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Complete operational/security gates, representative evaluation, and end-to-end documentation before release.

- [X] T070 [P] Add security response headers, API/body and upload limits, dependency lockfiles, local data ignore rules, and fail-closed production upload/workbook gates in `backend/src/invoice_assistant/api/main.py`, `backend/src/invoice_assistant/documents/intake.py`, `backend/src/invoice_assistant/api/routes.py`, `.gitignore`, and `.dockerignore`; rate limits, secure sessions, durable storage, and secret scanning remain open.
- [X] T071 [P] Add PII-safe process metrics for HTTP request routes, methods, and status codes in `backend/src/invoice_assistant/observability/metrics.py` and `backend/src/invoice_assistant/api/main.py`; production exporter and domain-specific metrics remain open.
- [X] T072 [P] Add keyboard focus states, semantic labels, status announcements, and responsive UI controls in `frontend/src/App.tsx` and `frontend/src/styles.css`; formal WCAG 2.2 AA audit remains open.
- [X] T073 Add workbook round-trip and formula-like text tests in `backend/tests/unit/test_workbook_adapter.py` and document supported/rejected OOXML features in `docs/workbook-support.md`; customer-specific fidelity still needs a representative corpus and spreadsheet-client review.
- [X] T074 Add available cross-boundary security tests for invalid/oversized uploads, workbook package abuse boundaries, formula-like values, workspace leakage, Origin/CSRF and role bypass in `backend/tests/test_upload_security.py`, `backend/tests/test_security_and_workbook_conflict.py`, and `backend/tests/unit/test_workbook_adapter.py`; isolated malicious-document sandbox tests remain gated on the worker implementation.
- [X] T075 Add evaluation runner and synthetic cases reporting deterministic check outcomes in `backend/scripts/evaluate_invoice_quality.py`, `backend/evaluation/synthetic-cases.json`, and `backend/evaluation/README.md`; approved-data OCR accuracy, duplicate recall, usability and AP-time metrics remain release gates requiring owner-approved data.
- [X] T076 Add a local prototype operations and safety runbook, including production blockers and disabled provider behavior, in `docs/operations-runbook.md`; production deployment/incident instructions remain gated.
- [X] T077 Run backend synthetic API/unit tests and frontend unit/build/lint/Playwright validation as documented in `specs/001-invoice-intake/quickstart.md`; backend: 49 tests, Ruff and mypy pass; frontend: 3 unit tests, build, ESLint and 2 Playwright tests pass. Production OCR/model evaluation and full workbook E2E remain gated and are not claimed.
- [ ] T078 Obtain and record AP, security/privacy, legal/provider, operations and release-owner approvals for policy defaults, provider routing/data terms, workbook allowlist, recovery tests, representative evaluation and production readiness in `docs/release-approvals/README.md`. This requires human approvals and cannot be completed by implementation automation.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No implementation dependencies; establishes projects and safe local fixtures.
- **Foundational (Phase 2)**: Depends on setup and blocks all story work. Authorization, workspace-scoped persistence, version contracts, audit and durable jobs are shared prerequisites.
- **US1 (Phase 3)**: Depends on Phase 2; provides upload, extraction proposal, evidence review and correction. MVP can use the deterministic fake provider; live OpenRouter processing is disabled until its provider gate passes.
- **US2 (Phase 4)**: Depends on Phase 2 and the reviewed draft contract from US1. Workbook read/mapping work can proceed alongside US1 after foundational contracts stabilize; end-to-end recording integrates both. Only application-managed workbook snapshots are included.
- **US3 (Phase 5)**: Depends on Phase 2; individual deterministic checks can be developed alongside US1/US2, while final recording-gate integration requires US2 publication and US1 draft versions.
- **Polish (Phase 6)**: Depends on the stories being released. Provider, security, workbook fidelity, performance/quality and owner approvals are mandatory production gates, not prerequisites for synthetic-only development.

### User Story Dependencies

- **US1 (P1)**: Starts after Phase 2; no dependency on spreadsheet publication. Independent value is a safe invoice review draft.
- **US2 (P2)**: Starts after Phase 2; its confirmation/write flow consumes the US1 draft contract and should integrate before delivery. It is the first story that publishes rows.
- **US3 (P3)**: Starts after Phase 2; checks can be implemented independently, but end-to-end pre-record verification integrates with US1 and US2.

### Within Each User Story

- Tests are included because the constitution requires automated coverage; implement the tests alongside/just before the component they verify.
- Persistence schemas and typed contracts precede services; services precede routes; routes precede UI integration.
- A task marked `[P]` touches files distinct from concurrent tasks and has no dependency on an unfinished task beyond its phase prerequisites.
- Commit or review coherent work groups; at each checkpoint run that story's focused tests and verify constitutional controls.

## Parallel Opportunities

- **Setup**: T002, T003, T004 and T007 can proceed in parallel after T001's directory setup; T005 and T006 are also independent.
- **Foundational**: T009–T011, T013, T015 and T019 can proceed in parallel after project setup. Database/RLS (T012) and schema/migrations (T008) must settle before persistence-backed domain tasks.
- **US1**: T023–T025; T027–T028; T030 can proceed in parallel after their shared schemas/interfaces are agreed. UI shell (T036) can proceed against the contract while extraction services are built.
- **US2**: T041–T044 can proceed in parallel; workbook inspection (T045) and mapping UI (T053) can proceed independently once API schemas are stable. Publication/idempotency tasks T050–T052 are sequentially dependent.
- **US3**: T057–T060 can proceed in parallel; T061 and T062 can proceed independently, as can UI T068 against the result schema. T063 precedes validation aggregation T064; T065 integrates with US2 publication.
- **Across stories**: After Phase 2 contracts are stable, teams can work on US1 UI, US2 workbook tooling, and US3 deterministic validators in parallel; integration dependencies listed above still apply.

## Parallel Example: User Story 3

```text
Parallel after shared policy/schema contracts:
- T057 decimal and currency tests in backend/tests/unit/test_total_validation.py
- T058 duplicate matcher tests in backend/tests/unit/test_duplicate_validation.py
- T061 required-field checks in backend/src/invoice_assistant/domain/required_field_checks.py
- T062 total checks in backend/src/invoice_assistant/domain/total_checks.py
- T068 validation panel in frontend/src/features/review/ValidationPanel.tsx
```

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 setup.
2. Complete Phase 2 foundational auth, persistence, contracts, audit and queue.
3. Complete Phase 3 US1 with the deterministic fake extraction provider and synthetic fixtures.
4. Verify editable evidence-backed draft, per-page failures, audit corrections, accessibility basics, workspace authorization, and that no row can be written without authorized confirmation.
5. Demonstrate to AP stakeholders using synthetic data. Do not enable external invoice processing until provider and privacy approval.

### Incremental Delivery

1. Setup and foundational security/persistence.
2. US1 reviewable intake MVP, synthetic/fake provider first.
3. US2 application-managed workbook mapping, version publication and explicit reviewer recording.
4. US3 deterministic exception/duplicate checking and final recording gate.
5. Polish, compatibility/security/quality evaluation and owner sign-off; production only after all release gates pass.

## Notes

- Every task has the required checkbox, sequential ID, optional parallel marker, required story label in story phases, and at least one explicit file path.
- `[P]` indicates parallelizable file-disjoint work, not just a task that could theoretically be delegated.
- A “record” action only creates an invoice-log entry; the application has no invoice approval or payment capability.
- Do not use actual invoice data or send data to OpenRouter/OCR until the organization approves data processing and the provider route is explicitly allowlisted.
