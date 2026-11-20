"""Versioned workspace policy validation."""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class WorkspacePolicy:
    version: int = 1
    required_fields: tuple[str, ...] = ("vendor_name", "invoice_number", "invoice_date", "currency", "total")
    hard_stop_fields: tuple[str, ...] = ("invoice_number", "total")
    allowed_overrides: tuple[str, ...] = ("missing_po", "duplicate_candidate", "low_confidence")
    currency_tolerance: dict[str, Decimal] = field(default_factory=lambda: {"USD": Decimal("0.01")})
    rounding: str = "ROUND_HALF_UP"
    min_uncertainty_confidence: Decimal = Decimal("0.70")


def validate_policy_update(data: dict[str, Any]) -> WorkspacePolicy:
    allowed = {"required_fields", "hard_stop_fields", "allowed_overrides", "currency_tolerance", "rounding", "min_uncertainty_confidence"}
    unknown = set(data) - allowed
    if unknown:
        raise ValueError(f"Unknown policy fields: {', '.join(sorted(unknown))}")
    base = WorkspacePolicy()
    fields = data.get("required_fields", base.required_fields)
    if not isinstance(fields, (tuple, list)) or any(not isinstance(item, str) for item in fields):
        raise ValueError("required_fields must be a list of field names")
    tolerances = data.get("currency_tolerance", base.currency_tolerance)
    normalized = {key.upper(): Decimal(str(value)) for key, value in tolerances.items()}
    if any(value < 0 for value in normalized.values()):
        raise ValueError("currency tolerance must not be negative")
    return WorkspacePolicy(
        version=base.version + 1,
        required_fields=tuple(fields),
        hard_stop_fields=tuple(data.get("hard_stop_fields", base.hard_stop_fields)),
        allowed_overrides=tuple(data.get("allowed_overrides", base.allowed_overrides)),
        currency_tolerance=normalized,
        rounding=str(data.get("rounding", base.rounding)),
        min_uncertainty_confidence=Decimal(str(data.get("min_uncertainty_confidence", base.min_uncertainty_confidence))),
    )
