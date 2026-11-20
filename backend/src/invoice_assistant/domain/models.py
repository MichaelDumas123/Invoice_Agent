"""Domain entities and explicit workflow state transitions."""

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class DraftStatus(StrEnum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    NEEDS_REVIEW = "needs_review"
    READY_FOR_REVIEW = "ready_for_review"
    RECORDED = "recorded"
    REJECTED = "rejected"
    FAILED = "failed"


class PageStatus(StrEnum):
    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"
    NOT_PROCESSED = "not_processed"


class DocumentRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: f"doc_{uuid4().hex}")
    workspace_id: str
    original_name: str
    detected_type: str
    checksum: str
    byte_size: int = Field(ge=1)
    page_count: int = Field(ge=1)
    status: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DraftRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: f"draft_{uuid4().hex}")
    workspace_id: str
    document_id: str
    version: int = Field(default=1, ge=1)
    status: DraftStatus = DraftStatus.NEEDS_REVIEW
    fields: dict[str, Any]
    pages: list[dict[str, Any]]
    warnings: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    recorded: bool = False


def transition_draft(draft: DraftRecord, target: DraftStatus) -> DraftRecord:
    allowed = {
        DraftStatus.UPLOADED: {DraftStatus.PROCESSING, DraftStatus.FAILED},
        DraftStatus.PROCESSING: {DraftStatus.NEEDS_REVIEW, DraftStatus.FAILED},
        DraftStatus.NEEDS_REVIEW: {DraftStatus.READY_FOR_REVIEW, DraftStatus.REJECTED, DraftStatus.FAILED},
        DraftStatus.READY_FOR_REVIEW: {DraftStatus.NEEDS_REVIEW, DraftStatus.RECORDED, DraftStatus.REJECTED},
        DraftStatus.FAILED: {DraftStatus.PROCESSING, DraftStatus.NEEDS_REVIEW},
        DraftStatus.REJECTED: {DraftStatus.NEEDS_REVIEW},
        DraftStatus.RECORDED: set(),
    }
    if target not in allowed[draft.status]:
        raise ValueError(f"Invalid draft transition: {draft.status.value} -> {target.value}")
    return draft.model_copy(update={"status": target, "updated_at": datetime.now(timezone.utc)})
