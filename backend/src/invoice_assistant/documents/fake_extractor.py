"""Deterministic fake extraction provider for explicitly synthetic test pages."""

from typing import Any

from invoice_assistant.api.schemas import FieldState


class FakeExtractor:
    async def extract(self, pages: list[bytes]) -> dict[str, Any]:
        if not pages:
            raise ValueError("At least one synthetic page is required")
        def absent(page: int) -> dict[str, Any]:
            return {"value": None, "state": FieldState.MISSING.value, "uncertainty": None, "evidence": {"page": page, "unavailable": "synthetic page contains no parseable data"}, "origin": "fake_provider"}

        return {name: absent(1) for name in ("vendor_name", "invoice_number", "invoice_date", "due_date", "po_number", "currency", "subtotal", "tax", "charges", "discount", "total")}
