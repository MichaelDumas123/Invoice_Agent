from decimal import Decimal

from invoice_assistant.api.schemas import ValidationStatus
from invoice_assistant.domain.policy import WorkspacePolicy
from invoice_assistant.domain.validation import (
    check_duplicates,
    check_required,
    check_total,
    normalize_identifier,
)


def fields(**overrides):
    result = {
        "vendor_name": {"value": "Acme Supply", "state": "present"},
        "invoice_number": {"value": "001-ABC", "state": "present"},
        "invoice_date": {"value": "2026-11-01", "state": "present"},
        "due_date": {"value": None, "state": "missing"},
        "po_number": {"value": None, "state": "missing"},
        "currency": {"value": "USD", "state": "present"},
        "subtotal": {"value": "100.00", "state": "present"},
        "tax": {"value": "8.00", "state": "present"},
        "charges": {"value": "0.00", "state": "present"},
        "discount": {"value": "0.00", "state": "present"},
        "total": {"value": "108.00", "state": "present"},
    }
    result.update(overrides)
    return result


def test_total_uses_decimal_and_currency_tolerance():
    result = check_total(fields(), WorkspacePolicy())
    assert result.status == ValidationStatus.PASS
    assert Decimal(result.evidence["calculated"]) == Decimal("108.00")


def test_total_is_inconclusive_when_component_missing():
    data = fields()
    data["tax"]["value"] = None
    assert check_total(data, WorkspacePolicy()).status == ValidationStatus.INCONCLUSIVE


def test_required_po_warns_but_does_not_claim_validation():
    results = check_required(fields(), WorkspacePolicy())
    po = next(item for item in results if item.check == "po_presence")
    assert po.status == ValidationStatus.WARNING
    assert "presence check only" in po.reason


def test_duplicate_match_uses_normalized_vendor_and_invoice_identifier():
    result = check_duplicates(fields(), [{"reference": "row-12", "vendor_name": "ACME-SUPPLY", "invoice_number": "001 ABC"}])
    assert result.status == ValidationStatus.WARNING
    assert result.references == ["row-12"]


def test_duplicate_is_inconclusive_if_identifiers_missing():
    data = fields()
    data["invoice_number"]["value"] = None
    assert check_duplicates(data, []).status == ValidationStatus.INCONCLUSIVE


def test_normalization_retains_leading_zeroes():
    assert normalize_identifier("00-12") == "0012"


def test_zero_decimal_currency_rounds_before_tolerance_comparison():
    data = fields()
    data["currency"]["value"] = "JPY"
    data["subtotal"]["value"] = "100.4"
    data["tax"]["value"] = "7.6"
    data["total"]["value"] = "108"
    result = check_total(data, WorkspacePolicy(currency_tolerance={"JPY": Decimal("0")}))
    assert result.status == ValidationStatus.PASS
