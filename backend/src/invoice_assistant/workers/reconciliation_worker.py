"""Development reconciliation helper for publication intents.

Production must reconcile pending object-store candidates against durable DB
transactions and must not publish until the review versions remain current.
"""

from typing import Any

from invoice_assistant.workbooks.record_intent_service import intents


async def reconcile_pending() -> list[dict[str, Any]]:
    """Return pending intent summaries; no automatic commit is performed."""
    return [{"workspace_id": item["workspace_id"], "idempotency_key": item["idempotency_key"], "status": item["status"], "action": "manual_review_required"} for item in intents.pending()]
