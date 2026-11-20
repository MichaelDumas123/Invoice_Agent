"""Audit domain service."""

from typing import Any

from invoice_assistant.persistence.audit_repository import repository


async def record_event(workspace_id: str, actor_id: str, action: str, resource_id: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return await repository.append(workspace_id, actor_id, action, resource_id, details)
