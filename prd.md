# Product Requirements Document: Accounts-Payable Invoice Assistant

## 1. Overview

### Problem
Accounts-payable (AP) staff receive invoices in inconsistent formats and manually transfer their contents into Excel. This work is time-consuming and susceptible to transcription errors, duplicate entries, missing purchase-order (PO) numbers, and arithmetic mistakes.

### Product vision
Provide a chat-based assistant that reads an uploaded invoice, extracts and checks its details, and prepares a row in the organization's existing Excel invoice log—or a newly created spreadsheet. The assistant highlights uncertainty and exceptions for human review. It never approves or pays an invoice.

### Goals
- Reduce manual invoice data entry while retaining the organization's existing spreadsheet format.
- Detect likely duplicates, missing PO numbers, and arithmetic discrepancies before a row is finalized.
- Make extracted values, source evidence, and warnings easy for AP staff to review and correct.
- Preserve a traceable human decision and prevent automated approval or payment.

### Non-goals
- Approving invoices, initiating payments, changing payment details, or connecting to banking systems.
- Automatically resolving discrepancies or making accounting and tax judgments on behalf of AP.
- Full ERP integration, vendor onboarding, or automated PO matching in the initial release.
- Guaranteeing that every invoice field can be extracted or every duplicate detected.

## 2. Users and roles

| Role | Needs | Permissions |
| --- | --- | --- |
| AP operator | Upload invoices, inspect extraction, correct fields, and maintain the invoice log. | Create and edit drafts; submit or save reviewed entries, subject to organizational permissions. |
| Authorized reviewer | Resolve flagged items and explicitly confirm whether an entry should be recorded. | Review and confirm or reject recording; this is not invoice approval. |
| Administrator | Configure access, spreadsheet mappings, validation rules, and retention policies. | Manage configuration and authorized users; no automatic payment or invoice approval. |

An individual may hold multiple roles if permitted by organizational policy. Authentication and authorization must be enforced server-side.

## 3. Scope and assumptions

- Initial inputs are PDF invoices, including scanned PDFs, and common image formats (JPEG, PNG, and iPhone HEIC/HEIF). Multi-page PDFs are supported. Upload limits and supported spreadsheet variants must be configurable and displayed in the UI.
- Initial spreadsheet support is `.xlsx`. Existing files are user-supplied or accessed through an explicitly configured, authorized storage integration. A new workbook can be generated when no log exists.
- The user selects a worksheet and maps recognized invoice fields to existing columns. Additional customer-specific columns are preserved and can be supplied by the user. Unsupported or ambiguous workbook features must be detected and surfaced before writing; the original must remain recoverable.
- The customer provides policies for mandatory fields, duplicate matching, monetary tolerance, access, retention, and permitted external processing. Defaults must be visible and configurable.
- The requested model identifier, `qwen/qwen3.7-flash`, is a configuration target; availability, exact OpenRouter model ID, and vision support must be verified before implementation. If the model cannot process images directly, an OCR/document-processing component is required. Never silently substitute a model or provider.
- An external PO system is not assumed. The initial missing-PO check only establishes whether a PO number is present; it does not verify that the PO exists or matches the invoice.

## 4. Primary user journey

1. An authorized user opens a chat and selects an existing workbook and worksheet or chooses to create a new log.
2. The user uploads an invoice and optionally provides instructions or corrections in chat.
3. The system validates the file, converts pages or images as needed, extracts invoice details, and presents the source alongside an editable structured draft.
4. Deterministic checks evaluate required fields, arithmetic, duplicates, and spreadsheet mapping. Warnings include their reasons and supporting values.
5. The user corrects the draft. Checks rerun after relevant changes. An authorized reviewer explicitly confirms recording or rejects the draft; unresolved warnings are shown at confirmation and require an explicit reason to proceed if organizational policy permits.
6. On confirmation, the backend writes one row to the selected log, returns the outcome and record reference, and retains the review and audit trail. If writing fails or the workbook changed, the draft remains available for recovery.

## 5. Functional requirements

### FR-1: Chat and document intake
- Provide a chat interface for uploading invoices, asking questions about extracted data, and requesting field edits. Chat instructions must not bypass permissions, validation, review, or the no-payment boundary.
- Accept the formats in scope, detect file type from content rather than filename alone, and clearly reject unsupported, malformed, encrypted, oversized, or unreadable files with actionable feedback.
- Decode HEIC/HEIF and render PDF pages into a processing-compatible representation while retaining the original file according to retention policy. Indicate conversion or OCR failures rather than silently skipping pages.
- Associate each document, conversation, draft, and processing result with the appropriate user and workspace.

### FR-2: Extraction and evidence
- Extract, where present: vendor name, invoice number, invoice date, due date, PO number, currency, subtotal, tax, shipping or other charges, discounts, and total. Support line items when they can be extracted reliably and are needed for validation or mapped output.
- Record each field's value, source location or page reference when available, and an uncertainty indicator. Distinguish missing, unreadable, and inferred values; do not invent missing data.
- Display the original invoice or a safe preview beside the editable extraction. The reviewer can inspect evidence and override values, with corrections recorded in the audit trail.
- Clearly label model-generated answers and extraction uncertainty. Treat invoice and chat content as untrusted data, not instructions that change system behavior.

### FR-3: Spreadsheet configuration and output
- Allow a user to upload/select an existing `.xlsx` log, inspect headers, select the destination worksheet, and map extracted fields to columns. Save reusable mappings scoped to the workspace and workbook template.
- Do not assume fixed column names or column order. Validate required mappings, destination permissions, header changes, and value types before recording. Prompt for unmapped required customer columns.
- Offer a new `.xlsx` workbook with sensible default columns and a configurable name and layout.
- Append a single row only after authorized confirmation. Preserve existing sheets, rows, formulas, formatting, and unrelated workbook content to the extent supported; identify unsupported features before writing and do not silently alter them. Protect against spreadsheet formula injection in untrusted text.
- Detect concurrent workbook changes before writing; stop and prompt the user to reload and recheck rather than overwrite another user's changes. Make write retries idempotent so the same confirmation cannot create duplicate rows.
- Report the workbook, worksheet, and row or stable record reference after a successful write. Provide a downloadable result when the workbook was uploaded locally.

### FR-4: Validation and exception handling
- Check required fields using configured policy. Flag a missing or unreadable PO number; do not assert a PO is valid merely because one is present.
- Compare the stated total with subtotal, tax, charges, and discounts when the required components are available. Use decimal arithmetic, the invoice currency, and a configurable tolerance; report the calculation and difference. If components are missing or ambiguous, mark the check as inconclusive rather than passing it. Where line items are available, optionally compare their sum with the subtotal and explain rounding assumptions.
- Detect potential duplicates against the selected log and records already recorded by this application in the same workspace. Use configurable normalized vendor and invoice-number matching, with amount, currency, and date as supporting signals; show matching record references and why they matched. Missing or ambiguous identifiers produce an inconclusive result, not a guarantee of uniqueness.
- Flag low-confidence extraction, conflicting fields, unsupported currency or date formats, failed checks, and other doubtful cases. Confidence thresholds are configurable and are not a guarantee of correctness.
- Rerun affected checks after edits and immediately before recording, including a fresh duplicate check against the current target log. Do not label an unperformed check as passed.

### FR-5: Human review and control
- Every invoice requires an explicit authorized human confirmation before a spreadsheet row is written. This action means only “record in the invoice log,” not approve or authorize payment.
- Show all unresolved warnings and their evidence at confirmation. Block recording for policy-defined hard stops; for overridable warnings, require an explicit acknowledgement and reason.
- Allow rejection or return to draft for corrections. Never automatically approve, pay, schedule payment, update payment instructions, or represent recording as financial approval.
- Use clear statuses such as `Uploaded`, `Processing`, `Needs review`, `Ready for review`, `Recorded`, `Rejected`, and `Failed`. A recorded row can still represent an invoice requiring separate business approval.

### FR-6: Audit and recovery
- Log document and draft identifiers, actor, timestamps, extraction and validation outcomes, edits, warning acknowledgements, confirmation or rejection, target workbook and row, and write failures. Avoid logging secrets or unnecessary invoice contents.
- Retain the original document, relevant evidence, and audit records according to configurable organizational retention and deletion policy. Record model/provider identifiers and relevant prompt or configuration versions for traceability without exposing secrets.
- Preserve drafts on processing or write failure, provide a clear retry path, and avoid duplicate writes on retries. No partial write may be presented as a successful recording.

## 6. Interface requirements

- **Chat workspace:** conversation history, upload control, processing status, and accessible error messages.
- **Invoice review:** document preview, editable fields, source references, confidence indicators, validation results, and duplicate candidates.
- **Spreadsheet setup:** workbook and worksheet selection, header preview, field mapping, and new-workbook creation.
- **Confirmation:** destination summary, changed values, unresolved warnings, acknowledgement/reason controls, and an explicit record action.
- **History:** searchable list of drafts and recorded or rejected invoices, subject to access permissions, with audit details.
- Support keyboard navigation, readable contrast, and screen-reader labels for key workflows; target WCAG 2.2 AA.

## 7. Technical approach

| Layer | Technology | Responsibility |
| --- | --- | --- |
| Frontend | React and TypeScript | Chat, uploads, spreadsheet setup, document preview, review, and confirmation. |
| API | FastAPI | Authentication and authorization, upload validation, draft and review APIs, workflow state, and controlled spreadsheet writes. |
| Backend | Python | Document conversion/OCR orchestration, deterministic validation, duplicate detection, spreadsheet processing, and audit events. |
| AI orchestration | LangChain | Structured extraction and conversational interactions with explicit schema validation and controlled tools. |
| Model provider | OpenRouter | Access to the configured `qwen/qwen3.7-flash` model, subject to verification and data-processing approval. |
| Persistence | Database and protected document storage; technologies to be selected | Drafts, mappings, record references, audit events, and retained documents. |

The model proposes structured data; application code validates it and performs all writes. Model output and document text must never directly execute commands or authorize privileged actions. Secrets are stored in a secrets manager or environment configuration, never in the frontend or source control. Define file-processing dependencies and hosting topology during technical design.

## 8. Security, privacy, and operational requirements

- Require authenticated access and enforce workspace isolation and role-based authorization for documents, logs, mappings, and review actions.
- Encrypt data in transit and at rest. Apply least-privilege storage access, malware scanning or equivalent upload controls, file-size limits, and safe parsing in an isolated processing environment.
- Send invoice content to OpenRouter only after the organization has approved the provider's terms, data handling, location, and retention practices. Minimize transmitted content where practical; do not promise zero retention without contractual verification.
- Protect against prompt injection, malicious files, unsafe spreadsheet formulas, and unauthorized cross-workspace access. Do not expose model credentials to clients.
- Provide monitoring for processing failures, model/provider errors, validation failures, write conflicts, and audit failures without placing sensitive invoice data in routine logs.
- Specify deployment-specific availability, backup, recovery, and incident-response targets before production launch. Spreadsheet writes should be atomic where supported; otherwise use a safe copy-and-replace strategy with recovery.

## 9. Success metrics

Measure against a documented pre-launch baseline using representative, consented invoices. Report results by input format, including scanned PDFs and HEIC, and track sample size and uncertainty.

| Metric | Proposed initial target |
| --- | --- |
| Median AP handling time per invoice | At least 30% lower than baseline. |
| Critical-field extraction accuracy | At least 95% per field on an agreed evaluation set; critical fields and scoring method to be defined before launch. |
| Duplicate detection | At least 95% recall on a labeled test set using the configured match rules; report false positives separately. |
| Total-check correctness | 100% of defined deterministic arithmetic test cases produce the expected pass, warning, or inconclusive result. |
| Unauthorized recording | Zero rows recorded without explicit authorized confirmation in security and workflow tests. |
| Approval/payment actions | Zero approval or payment capabilities and zero such actions initiated by the system. |

Targets are release goals, not guarantees; thresholds and evaluation datasets require stakeholder agreement.

## 10. Acceptance criteria

1. Given a readable supported PDF, scanned PDF, JPEG, PNG, or HEIC invoice, the user can upload it and review an editable draft with source references or an explicit indication that evidence is unavailable.
2. Given a multi-page invoice, all pages are processed or a visible failure identifies the pages that could not be processed. Unsupported or unreadable files are rejected or flagged without creating a log row.
3. Given an existing `.xlsx` log with custom headers and column order, a user can map fields and record a confirmed invoice in the intended worksheet without silently modifying unrelated content. A new workbook can also be created and downloaded.
4. Given an invoice with an absent or unreadable PO number, the draft shows a missing-PO warning; it does not claim to verify the PO against an external system.
5. Given sufficient monetary components, the system correctly compares the computed and stated totals using the configured tolerance; missing components produce an inconclusive check.
6. Given a likely duplicate in the selected log or application records, the review displays a candidate and match rationale. A missing identifier is not reported as a clean duplicate check.
7. Given a warning, an authorized reviewer sees it before recording; hard stops block recording, while an allowed override requires acknowledgement and a reason. Field changes trigger relevant rechecks.
8. Without explicit authorized confirmation, no row is written. Confirmation records only the log entry and cannot approve or pay the invoice.
9. If the workbook changes concurrently or a write fails, the user sees an actionable error, the draft is retained, and retrying does not create a second row.
10. The audit history identifies the actor, corrections, warnings, decision, and destination for a recorded invoice; unauthorized users cannot access another workspace's data.

## 11. Dependencies, risks, and open decisions

- **Model capability:** Confirm the exact OpenRouter model ID, availability, context limits, image input support, structured output behavior, cost, and data terms. Select an approved OCR fallback if needed.
- **Document quality:** Glare, handwriting, poor scans, and complex layouts may reduce accuracy. Human review remains mandatory.
- **Workbook compatibility:** Agree which `.xlsx` features are supported, how backups are retained, and whether shared/cloud-hosted logs require a separate integration.
- **Duplicate coverage:** Matching is limited to accessible configured sources; historic invoices outside them cannot be checked.
- **Policy:** Define required fields, hard stops versus overridable warnings, approval roles, duplicate rules, currency rounding and tolerance, and retention periods.
- **Operations:** Choose authentication, persistence, file storage, deployment, upload limits, supported locales, service-level objectives, and monitoring ownership.
- **Delivery sequencing:** Agree on representative invoice and workbook samples, evaluation criteria, and rollout plan before development.