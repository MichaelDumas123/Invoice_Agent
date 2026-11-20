# Implementation Plan: Invoice Intake and Review

**Branch**: `001-invoice-intake` (feature identifier; no Git branch was created) | **Date**: 2026-11-18 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-invoice-intake/spec.md`, `prd.md`, the project constitution, and the supplied React guidance.

## Summary

Build a chat-based AP intake and review workflow that extracts invoice proposals from PDFs and images, shows evidence and deterministic warnings, maps to a customer workbook, and records exactly one row only after an authorized human confirms. A FastAPI backend mediates all permissions, validation, review, durable auditing and spreadsheet writes. React/TypeScript provides the review UI; LangChain uses the configured OpenRouter model only for proposal generation. Immutable workbook snapshots and a transactional publication pointer protect application-managed logs.

## Technical Context

**Language/Version**: Python 3.12+; TypeScript 5.x; compatible locked versions selected at implementation.

**Primary Dependencies**: FastAPI, Pydantic, LangChain with OpenRouter integration, React, Vite, openpyxl, PDF renderer, HEIC decoder, and evaluated local Tesseract OCR fallback. Final versions and native dependencies require compatibility and security review.

**Storage**: PostgreSQL for workspace-scoped workflow, sessions, policies, version pointers and audit; private encrypted object storage for original documents, previews and immutable workbook snapshots.

**Testing**: pytest and HTTPX for backend unit/integration/contract tests; Vitest and Playwright for frontend, accessibility and end-to-end tests; representative consented document/workbook evaluation sets and fault injection.

**Target Platform**: Linux-hosted backend and sandboxed worker; modern desktop browsers over HTTPS. Organizational identity provider and deployment region require approval before release.

**Project Type**: Web application: Python API/worker and React SPA.

**Performance Goals**: At least 30% lower median AP handling time versus baseline; 95% critical-field accuracy and 95% duplicate recall on agreed evaluation sets; 90% unassisted upload-to-review task completion. No unapproved latency or throughput target is assumed.

**Constraints**: No approval, payment, or payment-instruction changes; every record requires authorized review; no external invoice processing before provider approval; accessible UI; safe file parsing; duplicate and arithmetic checks must be deterministic; workbook integrity and recovery must hold under conflicts and retries.

**Scale/Scope**: Initial single-document review flow with workspace isolation and uploaded/new `.xlsx` snapshots; volume and operating limits are configurable and must be agreed before production. Shared-drive/live external editing and ERP/PO matching are out of scope.

## Constitution Check

*Pre-research: PASS for the proposed architecture; implementation and launch remain gated by verification.*

| Principle | Design and verification gate |
| --- | --- |
| I. Human authority | Dedicated authenticated reviewer confirmation, bound to reviewed versions, is the sole recording path; no approval/payment tools or capabilities. Test all bypass attempts and retry cases. |
| II. Evidence and uncertainty | Structured draft records evidence, missing/unreadable/inferred states and corrections; UI exposes evidence and uncertainty. Test low-quality and multipage documents. |
| III. Deterministic checks | Server computes decimal totals, presence, duplicate and mapping checks; unknowns are inconclusive, hard stops block, overrides require reason. Revalidate before commit. |
| IV. Workbook integrity | Supported-feature allowlist, immutable staging, transactional version pointer, revalidation, conflict detection, idempotent confirmation and retained originals. Test client fidelity, conflicts and crash recovery. |
| V. Security and audit | OIDC sessions, CSRF protection, scoped authorization, private encrypted storage, isolated parsing and durable audit in the recording transaction. Provider and upstream processing require prior approval. |
| Stack and test gates | Python/FastAPI, React/TypeScript, LangChain and configured OpenRouter target are retained. No silent substitution; verify model capability and use OCR fallback if needed. Automated unit, integration, contract, security and failure tests gate release. |

**Post-design re-check**: PASS as a design; no principle exception is proposed. Production is blocked until the policy, provider, quality, security and workbook compatibility approvals documented in [research.md](research.md) are obtained. The constitution's unknown ratification date remains a governance follow-up, not an implementation decision.

## Project Structure

### Documentation (this feature)

```text
specs/001-invoice-intake/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── api.md
└── tasks.md             # created later by /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── pyproject.toml
├── src/invoice_assistant/
│   ├── api/              # scoped endpoints and request/response models
│   ├── auth/             # sessions, membership and authorization
│   ├── domain/           # drafts, checks, policies and state transitions
│   ├── documents/        # sandboxed intake and extraction adapters
│   ├── workbooks/        # mapping, fidelity and version publication
│   ├── workers/          # durable processing jobs
│   └── persistence/      # database, object store and audit repositories
└── tests/{unit,integration,contract}/
frontend/
├── package.json
├── src/{components,features,services}/
└── tests/{unit,e2e}/
```

**Structure Decision**: Separate backend and frontend projects share an API contract; generated clients derive from the running application's OpenAPI document. The tree is proposed and does not imply implementation exists. Independent reads may be parallelized and heavy previews lazy-loaded; user-initiated mutations stay in event handlers and sensitive data is not cached in browser storage.

## Complexity Tracking

No constitution violations or exceptions are proposed. The worker and immutable version store are justified by untrusted document processing and recoverable, concurrent spreadsheet writes.
