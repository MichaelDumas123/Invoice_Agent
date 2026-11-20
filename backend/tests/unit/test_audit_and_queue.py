import pytest

from invoice_assistant.domain.audit import make_audit_event
from invoice_assistant.workers.queue import InMemoryQueue


def test_audit_redacts_secrets_and_document_bytes():
    event = make_audit_event("ws", "u", "edit", "draft", {"token": "secret", "document_bytes": b"private", "fields": {"vendor_name": "Private Vendor"}, "field": "vendor"})
    assert event["details"]["token"] == "[REDACTED]"
    assert event["details"]["document_bytes"] == "[REDACTED]"
    assert event["details"]["fields"] == "[REDACTED]"
    assert event["details"]["field"] == "vendor"


@pytest.mark.asyncio
async def test_queue_claim_retry_preserves_workspace_and_increments_attempt():
    queue = InMemoryQueue()
    job = await queue.enqueue("ws", "process_document", {"document_id": "doc"})
    claimed = await queue.claim()
    assert claimed.id == job.id
    retry = await queue.retry(claimed)
    assert retry.workspace_id == "ws"
    assert retry.attempts == 1
