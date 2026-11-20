"""Deterministic invoice field, arithmetic, and duplicate checks."""

from decimal import Decimal, InvalidOperation
from typing import Any

from invoice_assistant.api.schemas import ValidationResult, ValidationStatus
from invoice_assistant.domain.policy import WorkspacePolicy


def _value(fields: dict[str, Any], name: str) -> Any:
    item = fields.get(name)
    return item.get("value") if isinstance(item, dict) else None


def check_required(fields: dict[str, Any], policy: WorkspacePolicy) -> list[ValidationResult]:
    results: list[ValidationResult] = []
    for name in policy.required_fields:
        value = _value(fields, name)
        if value is None or value == "":
            status = ValidationStatus.HARD_STOP if name in policy.hard_stop_fields else ValidationStatus.WARNING
            results.append(ValidationResult(check=f"required:{name}", status=status, reason=f"Required field {name} is missing or unreadable."))
        else:
            results.append(ValidationResult(check=f"required:{name}", status=ValidationStatus.PASS, reason=f"Required field {name} is present."))
    po = _value(fields, "po_number")
    if not po:
        results.append(ValidationResult(check="po_presence", status=ValidationStatus.WARNING, reason="No PO number was extracted; this is a presence check only."))
    return results


def check_total(fields: dict[str, Any], policy: WorkspacePolicy) -> ValidationResult:
    currency = str(_value(fields, "currency") or "").upper()
    names = ("subtotal", "tax", "charges", "discount", "total")
    values = {name: _value(fields, name) for name in names}
    if not currency or any(values[name] in (None, "") for name in names):
        return ValidationResult(check="total", status=ValidationStatus.INCONCLUSIVE, reason="Currency or monetary components are missing; total was not checked.")
    try:
        amounts = {name: Decimal(str(value)) for name, value in values.items()}
    except (InvalidOperation, ValueError):
        return ValidationResult(check="total", status=ValidationStatus.INCONCLUSIVE, reason="A monetary component is not a valid decimal amount.")
    calculated = amounts["subtotal"] + amounts["tax"] + amounts["charges"] - amounts["discount"]
    currency_precision = {"JPY": 0, "KRW": 0, "BHD": 3, "KWD": 3, "OMR": 3}
    precision = currency_precision.get(currency, 2)
    quantum = Decimal(1).scaleb(-precision)
    calculated = calculated.quantize(quantum)
    delta = abs(calculated - amounts["total"].quantize(quantum))
    tolerance = policy.currency_tolerance.get(currency)
    if tolerance is None:
        return ValidationResult(check="total", status=ValidationStatus.INCONCLUSIVE, reason=f"No rounding tolerance is configured for {currency}.", evidence={"calculated": str(calculated), "stated": str(amounts["total"])})
    status = ValidationStatus.PASS if delta <= tolerance else ValidationStatus.WARNING
    reason = "Invoice total reconciles within configured tolerance." if status == ValidationStatus.PASS else "Computed total differs from the stated total beyond configured tolerance."
    return ValidationResult(check="total", status=status, reason=reason, evidence={"currency": currency, "calculated": str(calculated), "stated": str(amounts["total"]), "difference": str(delta), "tolerance": str(tolerance)})


def normalize_identifier(value: Any) -> str:
    return "".join(character.casefold() for character in str(value or "") if character.isalnum())


def check_duplicates(fields: dict[str, Any], records: list[dict[str, Any]], selected_log_records: list[dict[str, Any]] | None = None) -> ValidationResult:
    vendor = normalize_identifier(_value(fields, "vendor_name"))
    number = normalize_identifier(_value(fields, "invoice_number"))
    if not vendor or not number:
        return ValidationResult(check="duplicate", status=ValidationStatus.INCONCLUSIVE, reason="Vendor or invoice number is missing or ambiguous; uniqueness cannot be established.")
    matches: list[str] = []
    for record in [*records, *(selected_log_records or [])]:
        old_vendor = normalize_identifier(record.get("vendor_name", record.get("vendor")))
        old_number = normalize_identifier(record.get("invoice_number", record.get("invoice")))
        if old_vendor == vendor and old_number == number:
            matches.append(str(record.get("reference", record.get("id", "unknown record"))))
    if matches:
        return ValidationResult(check="duplicate", status=ValidationStatus.WARNING, reason="A record with the same normalized vendor and invoice number may be a duplicate.", references=matches)
    return ValidationResult(check="duplicate", status=ValidationStatus.PASS, reason="No matching record was found in the checked sources.", evidence={"scope": "selected log and application workspace records"})


def validate_invoice(fields: dict[str, Any], policy: WorkspacePolicy, records: list[dict[str, Any]], selected_log_records: list[dict[str, Any]] | None = None) -> list[ValidationResult]:
    return [*check_required(fields, policy), check_total(fields, policy), check_duplicates(fields, records, selected_log_records)]
