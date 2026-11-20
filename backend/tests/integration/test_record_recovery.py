"""Development-mode recovery reporting tests; these do not prove crash-safe storage recovery."""

import pytest

from invoice_assistant.workbooks.record_intent_service import intents
from invoice_assistant.workers.reconciliation_worker import reconcile_pending


@pytest.mark.asyncio
async def test_pending_intents_are_reported_for_manual_review():
    key = "manual-recovery-test-0001"
    intents.begin("ws-recovery", key, b"candidate", {"workbook_id": "book", "expected_version": 1})
    pending = await reconcile_pending()
    assert any(item["workspace_id"] == "ws-recovery" and item["idempotency_key"] == key and item["action"] == "manual_review_required" for item in pending)
