"""In-memory, development-only storage for the synthetic-data MVP."""

from dataclasses import dataclass, field
from threading import RLock
from typing import Any


@dataclass
class WorkspaceData:
    drafts: dict[str, dict[str, Any]] = field(default_factory=dict)
    records: dict[str, dict[str, Any]] = field(default_factory=dict)
    workbooks: dict[str, dict[str, Any]] = field(default_factory=dict)
    mappings: dict[str, dict[str, Any]] = field(default_factory=dict)
    validation_runs: dict[str, dict[str, Any]] = field(default_factory=dict)
    policy: dict[str, Any] = field(default_factory=dict)
    documents: dict[str, dict[str, Any]] = field(default_factory=dict)
    conversations: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    idempotency: dict[str, tuple[str, dict[str, Any]]] = field(default_factory=dict)


class DemoStore:
    """Isolated ephemeral store. Not suitable for production or multi-process use."""

    def __init__(self) -> None:
        self._workspaces: dict[str, WorkspaceData] = {}
        self._lock = RLock()

    def workspace(self, workspace_id: str) -> WorkspaceData:
        with self._lock:
            return self._workspaces.setdefault(workspace_id, WorkspaceData())

    def put_draft(self, workspace_id: str, draft: dict[str, Any]) -> None:
        with self._lock:
            self.workspace(workspace_id).drafts[draft["id"]] = draft

    def get_draft(self, workspace_id: str, draft_id: str) -> dict[str, Any] | None:
        with self._lock:
            return self.workspace(workspace_id).drafts.get(draft_id)

    def reset(self) -> None:
        with self._lock:
            self._workspaces.clear()


store = DemoStore()
