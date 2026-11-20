"""Validate model proposals without treating generated content as authoritative."""

from typing import Any

from pydantic import ValidationError

from invoice_assistant.api.schemas import InvoiceFields


def validate_extraction(payload: dict[str, Any]) -> InvoiceFields:
    """Validate against the closed invoice-field schema; preserve evidence/state.

    Model confidence remains advisory text and never establishes correctness.
    """
    try:
        return InvoiceFields.model_validate(payload)
    except ValidationError as exc:
        raise ValueError("Extraction did not match the approved invoice schema") from exc
