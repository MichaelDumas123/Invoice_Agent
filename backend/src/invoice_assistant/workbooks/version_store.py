"""Immutable version staging with a database-like compare-and-swap pointer for tests."""

from dataclasses import dataclass
from hashlib import sha256
from uuid import uuid4

from invoice_assistant.persistence.object_store import MemoryObjectStore, StoredObject


@dataclass(frozen=True)
class WorkbookVersion:
    workbook_id: str
    workspace_id: str
    version: int
    object_key: str
    checksum: str
    parent_version: int | None


class VersionConflict(RuntimeError):
    pass


class WorkbookVersionStore:
    """Memory-only adapter; replace with a transactional DB/object-store implementation for production."""

    def __init__(self, objects: MemoryObjectStore | None = None) -> None:
        self.objects = objects or MemoryObjectStore()
        self._versions: dict[tuple[str, str, int], WorkbookVersion] = {}
        self._current: dict[tuple[str, str], int] = {}

    async def stage(self, workspace_id: str, workbook_id: str, expected_version: int, content: bytes) -> WorkbookVersion:
        current = self._current.get((workspace_id, workbook_id), 0)
        if current != expected_version:
            raise VersionConflict("Workbook changed; reload and review before recording")
        version = current + 1
        key = f"{workspace_id}/workbooks/{workbook_id}/versions/{version}-{uuid4().hex}.xlsx"
        stored: StoredObject = await self.objects.put_private(workspace_id, key, content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        candidate = WorkbookVersion(workbook_id, workspace_id, version, key, stored.etag or sha256(content).hexdigest(), current or None)
        self._versions[(workspace_id, workbook_id, version)] = candidate
        return candidate

    def publish(self, candidate: WorkbookVersion, expected_version: int) -> None:
        key = (candidate.workspace_id, candidate.workbook_id)
        if self._current.get(key, 0) != expected_version:
            raise VersionConflict("Workbook version compare-and-swap failed")
        self._current[key] = candidate.version

    def current_version(self, workspace_id: str, workbook_id: str) -> int:
        return self._current.get((workspace_id, workbook_id), 0)

    def seed(self, workspace_id: str, workbook_id: str, version: int) -> None:
        """Register an already-imported snapshot as the starting current version."""
        key = (workspace_id, workbook_id)
        current = self._current.get(key, 0)
        if current not in {0, version}:
            raise VersionConflict("Workbook version is already initialized differently")
        self._current[key] = version
