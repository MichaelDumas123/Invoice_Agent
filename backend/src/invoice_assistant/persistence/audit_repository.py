"""Audit repository interface with memory adapter for tests and demos."""

from typing import Any

from invoice_assistant.domain.audit import make_audit_event


class MemoryAuditRepository:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    async def append(self, workspace_id: str, actor_id: str, action: str, resource_id: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
        event = make_audit_event(workspace_id, actor_id, action, resource_id, details)
        self.events.append(event)
        return event

    async def for_resource(self, workspace_id: str, resource_id: str) -> list[dict[str, Any]]:
        return [event for event in self.events if event["workspace_id"] == workspace_id and event["resource_id"] == resource_id]


repository = MemoryAuditRepository()
