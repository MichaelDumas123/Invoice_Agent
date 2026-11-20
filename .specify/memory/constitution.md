<!--
Sync Impact Report
Version change: uninitialized template → 1.0.0
Modified principles: template placeholders → five invoice-assistant principles
Added sections: Product and Technical Constraints; Development and Review Workflow
Removed sections: none
Follow-up TODOs: confirm the original ratification date.
-->
# Accounts-Payable Invoice Assistant Constitution

## Core Principles

### I. Human Authority; No Approval or Payment
Only an authenticated, authorized human may confirm that an invoice draft is recorded in a spreadsheet. Recording is not invoice approval. The product MUST NOT approve, authorize, schedule, or pay an invoice; change payment instructions; or initiate a financial transaction. No model output, chat instruction, automated check, or retry may bypass this boundary. This separation prevents data-entry automation from exercising financial authority.

### II. Evidence-Based Extraction and Explicit Uncertainty
Extracted values MUST be traceable to invoice evidence when available. The system MUST distinguish missing, unreadable, and inferred values; MUST NOT invent values; and MUST present uncertainty and source evidence for human review. Users MUST be able to correct extracted values, and corrections MUST be auditable. Model-generated content is a proposal, never authoritative evidence by itself.

### III. Deterministic Checks; Fail Closed on Unknowns
Arithmetic, required-field checks, duplicate matching, permissions, and write eligibility MUST be evaluated by application logic with explicit, testable rules, not delegated to the language model. A check with insufficient or ambiguous evidence MUST be reported as inconclusive, never as passed. Policy-defined hard stops MUST block recording; permitted overrides MUST require authorized acknowledgement and a recorded reason. Relevant checks MUST rerun after edits and immediately before writing.

### IV. Preserve Spreadsheet and Record Integrity
The product MUST support user-configured mappings rather than assume fixed customer column names or order. It MUST validate the target and detect concurrent changes before writing, preserve unrelated workbook content to the extent supported, and surface unsupported features before modification. A row MUST be written only after explicit confirmation. Writes and retries MUST avoid duplicate or partial records; failures MUST leave the draft recoverable and MUST NOT be represented as successful.

### V. Protect Data and Maintain an Audit Trail
The system MUST enforce authenticated, workspace-scoped access and least privilege for documents, spreadsheets, mappings, and review actions. Invoice data MUST be protected in transit and at rest, and sent to an external model provider only under approved data-processing terms. Untrusted invoice and chat content MUST NOT alter system authority or execute tools. Material edits, checks, decisions, and write outcomes MUST be auditable without placing secrets or unnecessary invoice content in routine logs.

## Product and Technical Constraints

The initial product supports PDF (including scanned, multi-page documents), JPEG, PNG, and iPhone HEIC/HEIF invoice inputs, and `.xlsx` invoice logs. Unsupported or unreadable inputs and workbook features MUST be identified rather than silently skipped or altered. Where OCR or conversion fails, affected pages and fields MUST be visible to the reviewer.

The required application stack is Python for backend logic, FastAPI for the API, React with TypeScript for the frontend, and LangChain for LLM orchestration. OpenRouter is the configured model provider and `qwen/qwen3.7-flash` is the requested model target. Before production use, the team MUST verify the exact model identifier, availability, image and structured-output capabilities, costs, and data terms. The system MUST NOT silently substitute a provider or model. An approved OCR/document-processing component MUST be used if the selected model cannot process the required input.

The model MAY propose structured extraction but MUST NOT directly write to a spreadsheet or grant permissions. The backend MUST validate structured output against application schemas and business rules before it is shown or used. Credentials MUST remain server-side and outside source control. Spreadsheet text originating from an invoice MUST be handled to prevent formula injection.

## Development and Review Workflow

Changes to extraction, validation, duplicate detection, authorization, or spreadsheet writing MUST include automated tests for normal, invalid, ambiguous, and failure cases. Arithmetic checks MUST use decimal-safe calculations and configured currency tolerances. File-format, workbook-mapping, concurrency, retry-idempotency, workspace-isolation, and no-confirmation/no-write behavior MUST have integration or equivalent contract coverage before release.

Reviews MUST verify the applicable principles and acceptance criteria, including human confirmation, no approval/payment capability, visible uncertainty, and auditability. Security-sensitive changes and external data-processing changes require explicit review by an authorized project owner. Release readiness MUST include representative evaluation across supported formats and a documented review of model/provider behavior, unresolved policy decisions, and recovery paths.

## Governance

This constitution governs product and engineering decisions for the Accounts-Payable Invoice Assistant. If another project practice conflicts with it, the conflict MUST be raised and resolved through a constitution amendment before the conflicting practice is adopted. Amendments require a documented rationale, impact assessment, and approval by the designated project owner; changes affecting financial controls, privacy, or data processing also require the relevant security or business owner review. Reviewers MUST assess compliance during design and code review, and release owners MUST resolve or explicitly accept documented deviations before release.

Constitution versions follow semantic versioning. A MAJOR increment marks a backward-incompatible removal or redefinition of a principle or governance rule; a MINOR increment adds a principle or materially expands governance; a PATCH increment clarifies wording without changing obligations. Every amendment MUST update the version, last-amended date, and a temporary Sync Impact Report, and MUST identify required follow-up changes to project guidance. The Sync Impact Report is review scratch material and MUST be removed before the amended file is committed.

**Version**: 1.0.0 | **Ratified**: TODO(RATIFICATION_DATE): confirm original adoption date | **Last Amended**: 2026-11-17
