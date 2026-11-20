# Data Model: Invoice Intake and Review

All persistent records carry immutable IDs, workspace ID, creation/update timestamps and authorization scope. IDs are opaque and never grant access by themselves. All financial calculations use decimal values with currency and explicit rounding; string identifiers retain leading zeroes.

## Entities and relationships

| Entity | Essential fields | Relationships and rules |
| --- | --- | --- |
| Workspace | ID, policy version, active status | Owns all other entities; isolation is enforced on every read/write and worker job. |
| User and Membership | Identity-provider subject, workspace, roles (`operator`, `reviewer`, `administrator`) | Roles are explicit; admin does not imply reviewer. A user may have multiple roles. |
| PolicyVersion | Required fields, currency/rounding/tolerance, duplicate rules, confidence thresholds, hard-stop/override rules, retention/limits | Versioned, visible and workspace-scoped. A change invalidates affected draft checks and review. |
| Document | Original object key/hash, detected type, status, page count, uploader, retention metadata | Has many pages and drafts. Quarantined until validated and scanned; original remains recoverable. |
| DocumentPage | Index, conversion/extraction status, safe preview key, error code | Every page has a status; failed pages remain visible. Never silently claim success. |
| Draft | Document ID, version, status, fields, target workbook/mapping, current validation revision | One draft is associated with one workspace/document. Each material edit increments its version, marks affected validation stale, and invalidates prior confirmation. |
| InvoiceField | Field name, typed value or null, state (`present`, `missing`, `unreadable`, `inferred`), uncertainty, source/page reference or unavailable, origin (`model`, `user`) | Fields include vendor, invoice number, dates, PO, currency, subtotal, tax, charges, discount and total. User corrections retain prior audit history. |
| Conversation and Message | Draft/document, actor, text, created timestamp, response provenance | Workspace-scoped; content is untrusted and cannot grant authority or execute privileged actions. |
| Workbook | Name, current version ID, created/uploaded origin, selected worksheet, owner scope | Logical application-managed log; original local files are snapshots, not live targets. |
| WorkbookVersion | Workbook ID, parent version, immutable object key/hash, workbook feature inspection, creation status | Only a DB pointer identifies the current published version. Retain original and permitted backups. |
| FieldMapping | Workbook/template ID, worksheet, header signature, version, field-to-column map, required customer values | Header/mapping changes invalidate validation and review; preserve unmapped existing data. |
| ValidationRun and Result | Draft/version, policy/mapping/workbook versions, result type, status (`pass`, `warning`, `inconclusive`, `hard_stop`), evidence, calculation and duplicate candidates | Checks are application-owned, rerun after edits and immediately before publication; incomplete evidence never becomes pass. |
| ReviewDecision | Reviewer ID, action (`confirm_record`, `reject`, `return_to_draft`), draft/validation/mapping/policy/workbook versions, warning acknowledgements/reasons, timestamp | Only explicitly authorized reviewers may confirm. Hard stops forbid recording; overrides require reason. Any material change requires a new decision. |
| RecordIntent | ReviewDecision ID, workspace idempotency key, request fingerprint, expected workbook version, status, candidate object/hash and result reference | Unique `(workspace_id, idempotency_key)` and unique confirmation; same key with changed fingerprint is a conflict. Tracks safe staging and crash reconciliation. |
| RecordedInvoice | Draft/document ID, workbook/version, worksheet, row/reference, normalized vendor/invoice number, amount/currency/date, confirmation ID | Committed once per confirmation; visible only after pointer, record and audit commit. Supports cross-log duplicate checks in workspace. |
| AuditEvent | Actor/service identity, action, resource IDs, timestamps, versions, check/decision summary, outcome, override reason, provider/model/config version | Write a durable recording event in the same DB transaction as publication; avoid secrets or unnecessary invoice data in routine logs. Apply approved retention/deletion policy. |

## Validation and lifecycle

- Draft: `uploaded → processing → needs_review` or `ready_for_review`; edits or changed policy/target invalidate checks and move back to review; authorized rejection produces `rejected`. Processing failure produces `failed` with retained draft and retry path. Only an authorized, version-bound confirmation can transition to `recorded` after durable publication; `recorded` is not financial approval.
- `RecordIntent`: `pending → staging → committed`, or `conflict`/`failed`; retries with the same fingerprint return committed outcome or resume/reconcile pending state. An unreferenced candidate is never the current workbook.
- Validation considers subtotal + tax + charges − discounts versus total in the stated currency with configured tolerance and decimal-safe rounding; missing/ambiguous components yield inconclusive. Normalize configured vendor and invoice identifiers for matching, with amount, date and currency as supporting signals. Missing identifiers yield inconclusive.
- A workbook supports only documented tested OOXML features. Validate ZIP/XML limits, destination cell range, headers, mapped data types and string length; preserve legitimate formulas and serialize all untrusted text as strings, not formulas or hyperlinks. Reject unknown or unsupported features instead of risking silent loss.
- Publication holds a shared workspace-level duplicate-check/write coordination lock for all participating writers and a workbook-specific lock, rechecks the selected current log and application records, then stages and publishes. Locks and a version compare-and-swap must be backed by durable shared storage, not a process mutex. Different workspaces need not block one another.
- Database commit atomically advances a workbook pointer and records intent result, recorded invoice, and audit event. Object storage is outside the transaction: candidate key/hash must be reconciled after failures; garbage collection waits for a grace period and excludes active intents.
