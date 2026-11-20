# Feature Specification: Invoice Intake and Review

**Feature Branch**: `001-invoice-intake`

**Created**: 2026-11-18

**Status**: Draft

**Input**: User description: "Create a chat-based accounts-payable assistant that reads vendor invoices in PDF, scanned, and image formats, prepares entries in an existing or new Excel log, checks totals and duplicates, flags missing PO numbers and uncertainty for human review, and never approves or pays invoices. Use the product requirements document and project constitution as source constraints."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Prepare and review an invoice entry (Priority: P1)

An AP operator uploads an invoice and receives an editable draft of the invoice details, with a preview of the source, field evidence where available, and uncertainty clearly identified. The operator can correct values and see relevant checks rerun before an authorized reviewer confirms whether the invoice should be recorded in a spreadsheet.

**Why this priority**: Safe, reviewable data entry is the core product value and is the required path for every invoice.

**Independent Test**: Upload a readable invoice, inspect and edit the resulting draft, and confirm that no spreadsheet row is added until an authorized human explicitly confirms recording.

**Acceptance Scenarios**:

1. **Given** an authorized AP operator and a readable supported invoice, **When** the operator uploads it, **Then** the system presents an editable draft with the source preview and evidence or an explicit indication that evidence is unavailable.
2. **Given** a draft with uncertain or missing fields, **When** the operator reviews it, **Then** the system distinguishes missing, unreadable, and inferred values and does not invent a value.
3. **Given** a draft whose extracted value is incorrect, **When** the operator edits the value, **Then** the correction is recorded in the audit history and affected checks are rerun.
4. **Given** a reviewed draft, **When** nobody with recording authority confirms it, **Then** no invoice row is written.

---

### User Story 2 - Configure and record to an invoice log (Priority: P2)

An AP operator selects an existing Excel invoice log, chooses its worksheet, and maps invoice fields to the organization's columns, or chooses to create a new log. After review and authorized confirmation, the system records one entry and reports where it was written.

**Why this priority**: Writing to customer-specific logs completes the data-entry workflow after the safe review path is in place.

**Independent Test**: Map a sample invoice to a workbook with custom column names and ordering, confirm the draft, and verify that one row is added to the selected worksheet without changing unrelated content.

**Acceptance Scenarios**:

1. **Given** a supported existing workbook, **When** an authorized user selects a worksheet and maps fields to its headers, **Then** the system validates required mappings and shows the destination before confirmation.
2. **Given** no existing log, **When** the user requests a new log, **Then** the system offers a new spreadsheet with a clear default layout and configurable name.
3. **Given** a valid mapped draft and authorized confirmation, **When** recording succeeds, **Then** exactly one row is added and the workbook, worksheet, and row or stable record reference are reported.
4. **Given** a workbook with changed headers or a concurrent update, **When** the user attempts to record, **Then** the system stops, explains the conflict, and asks the user to reload and recheck rather than overwrite changes.

---

### User Story 3 - Identify exceptions and likely duplicates (Priority: P3)

An AP operator or reviewer sees actionable warnings when a PO number is absent, monetary components do not reconcile, invoice details may duplicate an existing record, or extraction is uncertain. The reviewer can resolve the issue or apply an allowed override with an acknowledgement and reason.

**Why this priority**: Exception detection reduces avoidable entry errors, while clear human decisions keep uncertain cases controlled.

**Independent Test**: Submit invoices with missing PO values, inconsistent totals, and duplicate identifiers and verify that the corresponding warnings include reasons and evidence and cannot silently pass.

**Acceptance Scenarios**:

1. **Given** an invoice with no readable PO number, **When** validation runs, **Then** the system displays a missing-PO warning and does not claim the PO was checked against an external system.
2. **Given** sufficient monetary components, **When** validation runs, **Then** the system compares the stated and computed totals using the configured currency tolerance and shows the calculation and difference.
3. **Given** insufficient or ambiguous monetary components, **When** validation runs, **Then** the total check is inconclusive rather than passed.
4. **Given** a likely matching invoice in an accessible log, **When** duplicate detection runs, **Then** the candidate, match rationale, and record reference are shown; absent or ambiguous identifiers produce an inconclusive result.
5. **Given** a policy-defined hard-stop warning, **When** a reviewer attempts to record the invoice, **Then** the action is blocked; for an allowed override, **Then** authorized acknowledgement and a reason are required and audited.

---

### Edge Cases

- A malformed, encrypted, unsupported, oversized, or unreadable file is rejected with actionable feedback and does not create a spreadsheet row.
- A multi-page invoice with one or more pages that fail conversion or OCR identifies the affected pages; it does not silently treat the document as fully processed.
- A file's actual content does not match its filename extension; the system validates content and rejects or flags unsafe or unsupported content.
- A scan, phone photo, or HEIC image is blurry, rotated, cropped, or contains handwriting; uncertain fields are flagged for review.
- Invoice text or chat instructions attempt to change system rules, bypass review, or initiate payment; the request does not change authorization or workflow boundaries.
- A spreadsheet contains unsupported features, formulas, unexpected headers, invalid destination values, or formula-like invoice text; the system warns or safely handles the content without silently corrupting the workbook or executing formulas.
- A target workbook changes between review and write; recording is stopped and the user is asked to reload and rerun checks.
- A write or model-provider request fails or times out; the draft is retained, the failure is visible, and retrying the same confirmation cannot create a duplicate row.
- An external provider is not approved for invoice data or its model identifier/capabilities cannot be verified; invoice contents are not sent until approval and required capability checks are complete.
- A duplicate candidate is outside the selected log and application records accessible to the workspace; the system does not claim global duplicate coverage.
- A user from another workspace attempts to access a document, draft, mapping, log, or review action; access is denied.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST accept supported PDF invoices (including scanned and multi-page PDFs), JPEG, PNG, and HEIC/HEIF images, and MUST provide actionable feedback for unsupported, malformed, encrypted, oversized, or unreadable inputs.
- **FR-002**: The system MUST process all pages or identify each page that failed conversion or extraction; it MUST NOT silently skip pages.
- **FR-003**: The system MUST produce an editable draft containing invoice fields where present, including vendor, invoice number, invoice and due dates, PO number, currency, subtotal, tax, additional charges, discounts, and total; line items MAY be included when reliably available and needed.
- **FR-004**: For each extracted field, the system MUST provide source location or page evidence when available and an uncertainty indicator, and MUST distinguish missing, unreadable, and inferred values without inventing data.
- **FR-005**: The system MUST display a safe source preview with the extracted draft and allow authorized users to correct values; corrections MUST be audited.
- **FR-006**: The chat experience MUST support invoice questions and draft corrections, but chat and document content MUST NOT bypass authorization, validation, review, or the prohibition on approval and payment.
- **FR-007**: The system MUST support user-selected existing `.xlsx` workbooks and worksheets, header inspection, and field mapping without assuming fixed column names or order.
- **FR-008**: The system MUST validate required mappings, destination permissions, changed headers, and value types, and MUST prompt for unmapped required customer columns before recording.
- **FR-009**: The system MUST offer creation of a new spreadsheet with a clear default layout and configurable name.
- **FR-010**: The system MUST write exactly one invoice row only after explicit authorized human confirmation that means recording in a log, not invoice approval. The system MUST never approve, authorize, schedule, or pay an invoice, change payment instructions, or initiate a financial transaction.
- **FR-011**: The system MUST preserve unrelated workbook content to the extent supported, identify unsupported features before writing, protect against formula injection, and ensure retries do not duplicate a row.
- **FR-012**: The system MUST detect concurrent target workbook changes before writing and stop for reload and revalidation rather than overwrite another user's changes.
- **FR-013**: The system MUST report the workbook, worksheet, and row or stable record reference after a successful write and provide a downloadable result for a locally uploaded workbook.
- **FR-014**: The system MUST check configured required fields and flag a missing or unreadable PO number without claiming external PO validation.
- **FR-015**: The system MUST compare totals with decimal-safe arithmetic when sufficient components are available, apply configured currency tolerance, and display the calculation and difference; otherwise the check MUST be inconclusive.
- **FR-016**: The system MUST detect potential duplicates against the selected log and records recorded by the application in the same workspace, show match rationale and references, and report inconclusive when identifiers are missing or ambiguous.
- **FR-017**: The system MUST flag low-confidence, conflicting, unsupported, and failed validation results. Relevant checks MUST rerun after edits and immediately before recording; unperformed checks MUST NOT be reported as passed.
- **FR-018**: The system MUST display warnings and evidence before confirmation, block policy-defined hard stops, and require authorized acknowledgement and a reason for policy-permitted overrides.
- **FR-019**: The system MUST provide clear processing and review statuses and support rejection or return to draft without recording a row.
- **FR-020**: The system MUST maintain an audit history of document/draft identifiers, actors, timestamps, extraction and validation outcomes, edits, warning acknowledgements, decisions, destinations, write outcomes, and failures while avoiding secrets and unnecessary invoice contents in routine logs.
- **FR-021**: The system MUST retain drafts on processing and write failures, support safe recovery, and MUST NOT present a partial or failed write as successful.
- **FR-022**: The system MUST enforce authenticated, role-based, workspace-scoped access to documents, conversations, drafts, mappings, logs, and review actions.
- **FR-023**: Invoice data MUST be sent to an external model provider only after the organization approves the provider's terms, data handling, location, and retention practices; provider/model identity and relevant configuration versions MUST be traceable without exposing credentials.
- **FR-024**: The product MUST provide keyboard-accessible controls, readable contrast, and screen-reader labels for key workflows, targeting WCAG 2.2 AA.
- **FR-025**: The configured model target MUST be `qwen/qwen3.7-flash` through OpenRouter unless explicitly changed through an approved configuration decision; actual identifier, availability, vision and structured-output capabilities, costs, and data terms MUST be verified before production. No model or provider substitution may occur silently.

### Key Entities *(include if feature involves data)*

- **Invoice Document**: An uploaded source file and its pages, file type, processing status, and retention/deletion state.
- **Invoice Draft**: Editable extracted invoice fields, source evidence, uncertainty, validation results, lifecycle status, and associated document.
- **Invoice Field**: A named invoice value with extracted or corrected content, source evidence, and uncertainty state.
- **Validation Result**: A required-field, total, duplicate, or other check outcome with status, rationale, evidence, and applicable policy.
- **Spreadsheet Log**: A selected or newly created workbook and worksheet, its headers, mapped fields, and record references.
- **Field Mapping**: A reusable workspace-scoped relationship between invoice fields and customer spreadsheet columns.
- **Review Decision**: An authorized human's confirmation, rejection, or warning override, including actor, time, and reason where required.
- **Audit Event**: A traceable event for processing, edits, validations, review decisions, and spreadsheet write outcomes.
- **Workspace and User Role**: A security boundary and the permissions applicable to users acting on its documents, drafts, logs, and decisions.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a representative evaluation, median AP handling time per invoice is reduced by at least 30% compared with a documented pre-launch baseline.
- **SC-002**: Critical-field extraction accuracy reaches at least 95% per field on an agreed, consented evaluation set, reported separately by supported input format.
- **SC-003**: Duplicate detection achieves at least 95% recall on a labeled evaluation set for the configured match rules, with false positives reported separately.
- **SC-004**: All defined deterministic arithmetic test cases return the expected pass, warning, or inconclusive outcome.
- **SC-005**: Zero invoice rows are recorded without an explicit authorized human confirmation in acceptance and security tests.
- **SC-006**: The product has zero approval or payment capabilities and initiates zero approval or payment actions.
- **SC-007**: At least 90% of representative AP users can complete the upload-to-review task and identify the required next action without assistance during usability testing.

## Assumptions

- Initial spreadsheet format is `.xlsx`; spreadsheets requiring unsupported features or macros are rejected or flagged before any write.
- Existing workbooks are uploaded by a user or made available through a separately authorized integration; no shared-drive integration is assumed.
- Authentication, storage, database, deployment, upload limits, locale coverage, service-level objectives, and retention periods will be selected during technical planning and must satisfy the privacy and security requirements.
- Required fields, hard stops, overridable warnings, duplicate thresholds, currency tolerance, and rounding rules are workspace-configurable and visible to users.
- A PO number is checked for presence only; no external PO matching is included in the initial release.
- The requested OpenRouter model target and its capabilities and data terms are subject to verification before production; an approved OCR/document-processing component is required if direct vision processing is not available.
- The recorded action stores invoice data in a log only and does not constitute approval for payment or substitute for any separate business approval process.
