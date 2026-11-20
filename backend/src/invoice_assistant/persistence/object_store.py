"""Private object-store abstraction and in-memory test implementation."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class StoredObject:
    key: str
    etag: str
    size: int


class ObjectStore(Protocol):
    async def put_private(self, workspace_id: str, key: str, content: bytes, content_type: str) -> StoredObject: ...
    async def get_private(self, workspace_id: str, key: str) -> bytes: ...
    async def delete_private(self, workspace_id: str, key: str) -> None: ...


class MemoryObjectStore:
    """Non-durable local test adapter; not for production or real invoice data."""

    def __init__(self) -> None:
        self._objects: dict[tuple[str, str], bytes] = {}

    async def put_private(self, workspace_id: str, key: str, content: bytes, content_type: str) -> StoredObject:
        if not workspace_id or not key.startswith(f"{workspace_id}/"):
            raise PermissionError("Object keys must be scoped to the active workspace")
        self._objects[(workspace_id, key)] = content
        import hashlib
        return StoredObject(key=key, etag=hashlib.sha256(content).hexdigest(), size=len(content))

    async def get_private(self, workspace_id: str, key: str) -> bytes:
        if not key.startswith(f"{workspace_id}/"):
            raise PermissionError("Workspace mismatch")
        try:
            return self._objects[(workspace_id, key)]
        except KeyError as exc:
            raise FileNotFoundError(key) from exc

    async def delete_private(self, workspace_id: str, key: str) -> None:
        self._objects.pop((workspace_id, key), None)


object_store: ObjectStore = MemoryObjectStore()
