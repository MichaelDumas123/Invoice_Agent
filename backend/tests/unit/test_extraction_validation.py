import pytest

from invoice_assistant.documents.extraction_validation import validate_extraction


def test_rejects_unknown_model_fields():
    with pytest.raises(ValueError, match="approved invoice schema"):
        validate_extraction({"untrusted_tool": "run payment"})


def test_preserves_missing_and_unreadable_states():
    blank = {"value": None, "state": "missing", "uncertainty": None, "evidence": None}
    unreadable = {"value": None, "state": "unreadable", "uncertainty": "blurred", "evidence": {"page": 1}}
    payload = {name: blank for name in InvoiceFieldNames}
    payload["po_number"] = unreadable
    result = validate_extraction(payload)
    assert result.po_number.state.value == "unreadable"
    assert result.po_number.uncertainty == "blurred"


InvoiceFieldNames = (
    "vendor_name",
    "invoice_number",
    "invoice_date",
    "due_date",
    "po_number",
    "currency",
    "subtotal",
    "tax",
    "charges",
    "discount",
    "total",
)
