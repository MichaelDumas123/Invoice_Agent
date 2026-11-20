"""Public API schemas for invoice review."""

from datetime import date, datetime, timezone
from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Role(StrEnum):
    OPERATOR = "operator"
    REVIEWER = "reviewer"
    ADMINISTRATOR = "administrator"


class FieldState(StrEnum):
    PRESENT = "present"
    MISSING = "missing"
    UNREADABLE = "unreadable"
    INFERRED = "inferred"


class ValidationStatus(StrEnum):
    PASS = "pass"
    WARNING = "warning"
    INCONCLUSIVE = "inconclusive"
    HARD_STOP = "hard_stop"


class InvoiceField(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: str | Decimal | date | None = None
    state: FieldState
    uncertainty: str | None = None
    evidence: dict[str, Any] | None = None
    origin: str = "unavailable"


class InvoiceFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vendor_name: InvoiceField
    invoice_number: InvoiceField
    invoice_date: InvoiceField
    due_date: InvoiceField
    po_number: InvoiceField
    currency: InvoiceField
    subtotal: InvoiceField
    tax: InvoiceField
    charges: InvoiceField
    discount: InvoiceField
    total: InvoiceField


class DocumentPage(BaseModel):
    page: int = Field(ge=1)
    status: str
    preview_url: str | None = None
    error: str | None = None


class DraftView(BaseModel):
    id: str
    document_id: str
    workspace_id: str
    version: int
    status: str
    fields: InvoiceFields
    pages: list[DocumentPage]
    warnings: list[str] = Field(default_factory=list)
    audit: list[dict[str, str]] = Field(default_factory=list)
    recorded: bool = False


class CorrectionRequest(BaseModel):
    field_name: str
    value: str = Field(max_length=32767)
    expected_version: int = Field(ge=1)


class DocumentResponse(BaseModel):
    id: str
    status: str
    detected_type: str
    byte_size: int
    checksum: str
    page_count: int
    pages: list[DocumentPage]
    error: str | None = None


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    message: str
    source: str = "deterministic_demo"
    proposed_corrections: dict[str, str] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    code: str
    message: str
    request_id: str | None = None


class RecordIntent(BaseModel):
    """Intentionally has no approval/payment operation."""

    draft_id: str
    reason: str = Field(min_length=1, max_length=1000)
    idempotency_key: str = Field(min_length=16, max_length=128)
    expected_version: int = Field(ge=1)


class RecordResult(BaseModel):
    status: str
    reference: str
    message: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ValidationResult(BaseModel):
    check: str
    status: ValidationStatus
    reason: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    references: list[str] = Field(default_factory=list)


class ValidationRun(BaseModel):
    id: str
    draft_id: str
    draft_version: int
    policy_version: int
    results: list[ValidationResult]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MappingRequest(BaseModel):
    worksheet: str = Field(min_length=1, max_length=128)
    expected_version: int = Field(ge=0)
    field_to_column: dict[str, int]
    required_fields: list[str] = Field(default_factory=list)


class RecordRequest(BaseModel):
    draft_id: str
    workbook_id: str
    validation_id: str
    draft_version: int = Field(ge=1)
    workbook_version: int = Field(ge=1)
    mapping_version: int = Field(ge=1)
    reason: str = Field(min_length=1, max_length=1000)
    idempotency_key: str = Field(min_length=16, max_length=128)
    acknowledgements: list[dict[str, str]] = Field(default_factory=list, max_length=50)


class PolicyUpdateRequest(BaseModel):
    expected_version: int = Field(ge=1)
    payload: dict[str, Any]
