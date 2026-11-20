import pytest

from invoice_assistant.domain.models import DraftRecord, DraftStatus, transition_draft
from invoice_assistant.domain.policy import validate_policy_update


def blank_fields():
    return {name: {"value": None, "state": "missing", "evidence": {"unavailable": "not processed"}} for name in (
        "vendor_name", "invoice_number", "invoice_date", "due_date", "po_number", "currency", "subtotal", "tax", "charges", "discount", "total"
    )}


def test_draft_transition_rejects_recording_without_review_state():
    draft = DraftRecord(workspace_id="ws", document_id="doc", fields=blank_fields(), pages=[])
    with pytest.raises(ValueError, match="Invalid draft transition"):
        transition_draft(draft, DraftStatus.RECORDED)


def test_draft_can_fail_then_reprocess():
    draft = DraftRecord(workspace_id="ws", document_id="doc", status=DraftStatus.FAILED, fields=blank_fields(), pages=[])
    assert transition_draft(draft, DraftStatus.PROCESSING).status == DraftStatus.PROCESSING


def test_policy_rejects_negative_tolerance_and_unknown_properties():
    with pytest.raises(ValueError, match="negative"):
        validate_policy_update({"currency_tolerance": {"USD": "-0.01"}})
    with pytest.raises(ValueError, match="Unknown policy"):
        validate_policy_update({"allow_payment": True})
