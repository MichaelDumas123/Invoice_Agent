"""Synthetic deterministic draft generation and safe demo workflow."""

from datetime import datetime, timezone
from hashlib import sha256
from typing import Any
from uuid import uuid4

from invoice_assistant.api.schemas import FieldState
from invoice_assistant.domain.store import store


def make_field(value: Any = None, *, page: int | None = None, uncertainty: str | None = None) -> dict[str, Any]:
    state = FieldState.MISSING if value is None else FieldState.PRESENT
    return {
        "value": str(value) if value is not None else None,
        "state": state.value,
        "uncertainty": uncertainty,
        "evidence": {"page": page, "location": "demo sample"} if value is not None else {"unavailable": "document was not processed"},
        "origin": "unavailable",
    }


def create_demo_draft(workspace_id: str, filename: str, detected_type: str, content: bytes) -> dict:
    checksum = sha256(content).hexdigest()
    doc_id = f"doc_{uuid4().hex[:12]}"
    draft_id = f"draft_{uuid4().hex[:12]}"
    fields = {
        "vendor_name": make_field(None),
        "invoice_number": make_field(None),
        "invoice_date": make_field(None),
        "due_date": make_field(None),
        "po_number": make_field(None),
        "currency": make_field(None),
        "subtotal": make_field(None),
        "tax": make_field(None),
        "charges": make_field(None),
        "discount": make_field(None),
        "total": make_field(None),
    }
    now = datetime.now(timezone.utc).isoformat()
    draft = {
        "id": draft_id,
        "document_id": doc_id,
        "workspace_id": workspace_id,
        "version": 1,
        "status": "needs_review",
        "filename": filename,
        "detected_type": detected_type,
        "checksum": checksum,
        "byte_size": len(content),
        "fields": fields,
        "pages": [{"page": 1, "status": "not_processed", "preview_url": None, "error": "Document rendering and extraction are not implemented in the demo."}],
        "warnings": ["Invoice extraction is not implemented; all fields are missing and validation is inconclusive."],
        "audit": [{"event": "draft_created", "at": now, "actor": "demo", "detail": f"Uploaded document {checksum[:12]} validated only; no OCR, preview or external model was used."}],
        "recorded": False,
        "created_at": now,
    }
    store.put_draft(workspace_id, draft)
    return draft
