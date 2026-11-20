# Quickstart and Validation Guide

This guide describes the **planned** implementation and cannot be run until `/speckit-tasks` and implementation create the named projects, fixtures, scripts and services. Do not treat these commands as already verified.

## Prerequisites and setup

- Python 3.12+, Node.js/npm, a container runtime, and a local test PostgreSQL/object store and identity provider as defined by the implementation's development configuration.
- Synthetic test invoices in PDF (including multipage scan), JPEG, PNG and HEIC, plus supported/unsupported sample `.xlsx` logs. Do not use real invoice data without explicit authorization.
- Configure a test workspace with an operator and reviewer, versioned validation policy and a deterministic fake model/OCR provider. Disable external model access for routine tests. For provider integration, obtain explicit organizational approval before using real data; verify exact model/endpoint and routing first.
- The implementation must provide a documented development environment, dependency lockfiles, migrations, test fixtures and `.env.example` without secrets. Initial illustrative commands, to be aligned with actual manifests and service definitions:

```bash
# After implementation provides backend/pyproject.toml and dependencies:
cd backend
python -m pytest tests/unit tests/integration tests/contract

# After implementation provides frontend/package.json and test scripts:
cd ../frontend
npm ci
npm run test
npm run build
npm run test:e2e
```

Run backend and frontend using the commands documented by the implemented projects; use test credentials and isolated local services. See [API contract](contracts/api.md) and [data model](data-model.md) for expected behavior.

## End-to-end checks

1. Sign in as an operator; upload each supported synthetic invoice type. Check processing status, page coverage, editable fields, source evidence or explicit absence, and uncertainty. Unreadable or unsupported input produces an actionable error without a row.
2. Select a custom-header workbook and worksheet, map fields, correct a draft and verify relevant checks rerun. A second workspace must not access the draft, source, log or preview.
3. Verify missing PO, inconsistent totals, incomplete components and a likely duplicate produce respectively a warning, warning, inconclusive result and candidate with rationale. Correcting an issue updates its result. A hard stop blocks; an allowed override requires an acknowledgement and reason.
4. As operator, attempt recording and verify denial. As reviewer, inspect the destination and warnings and confirm recording. Verify exactly one row, correct mapping, downloadable workbook, audit actor/reason, and clear wording that recording is not approval or payment.
5. Retry the same confirmation and simulate a lost response: the result is unchanged and only one row exists. Change a workbook or draft during review: recording returns conflict, preserves the draft, and requires reload and renewed review.
6. Inject failures before and after candidate staging and database publication; reconcile safely, do not expose staged-only objects, and verify no partial or duplicated publication. Test concurrent recordings, including two candidate duplicates targeting different logs within the same workspace.
7. Exercise malicious uploads, formula-like text, oversized/decompression-bomb files, cross-workspace requests, CSRF failures, and document/chat prompt injection. Verify no security control or confirmation is bypassed. Test keyboard navigation, screen-reader labels and contrast.
8. With approved representative data, evaluate critical-field accuracy and duplicate recall by format, AP time baseline, workbook round-trip fidelity and human usability. Record results and required owner approvals before production.
