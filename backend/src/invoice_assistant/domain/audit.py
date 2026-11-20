"""PII-minimizing audit event construction."""

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

SENSITIVE_KEYS = {"model_api_key", "authorization", "token", "password", "secret", "document_bytes", "content", "invoice_number", "vendor_name", "email", "account_number", "invoice_fields", "fields"}


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: "[REDACTED]" if key.lower() in SENSITIVE_KEYS or "password" in key.lower() or "token" in key.lower() or "secret" in key.lower() or key.lower().endswith("_key") else redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def make_audit_event(workspace_id: str, actor_id: str, action: str, resource_id: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "id": f"audit_{uuid4().hex}",
        "workspace_id": workspace_id,
        "actor_id": actor_id,
        "action": action,
        "resource_id": resource_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "details": redact(details or {}),
    }
