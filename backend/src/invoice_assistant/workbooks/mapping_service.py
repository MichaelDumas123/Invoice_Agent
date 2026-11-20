"""Workspace-scoped in-memory workbook mapping service for the local prototype."""

from dataclasses import dataclass
from hashlib import sha256
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class MappingRecord:
    id: str
    workspace_id: str
    workbook_id: str
    worksheet: str
    header_signature: str
    field_to_column: dict[str, int]
    required_customer_columns: tuple[str, ...]
    version: int


class MappingStore:
    def __init__(self) -> None:
        self._items: dict[tuple[str, str], MappingRecord] = {}

    def save(self, workspace_id: str, workbook_id: str, worksheet: str, headers: list[str], mapping: dict[str, int], required: list[str] | None = None, expected_version: int | None = None) -> MappingRecord:
        if not workspace_id or not workbook_id or not worksheet:
            raise ValueError("Workspace, workbook, and worksheet are required")
        if any(not isinstance(field, str) or not field.isidentifier() for field in mapping):
            raise ValueError("Mapping field keys must be valid field identifiers")
        if len(set(mapping.values())) != len(mapping):
            raise ValueError("Each invoice field must map to a different workbook column")
        if any(column < 1 or column > len(headers) for column in mapping.values()):
            raise ValueError("Mapping refers to a column outside the inspected header row")
        missing = set(required or ()) - set(mapping)
        if missing:
            raise ValueError(f"Required fields are unmapped: {', '.join(sorted(missing))}")
        signature = sha256("\x1f".join(headers).encode()).hexdigest()
        key = (workspace_id, workbook_id)
        previous = self._items.get(key)
        if expected_version is not None and (previous.version if previous else 0) != expected_version:
            raise ValueError("Mapping version changed; reload before updating")
        version = previous.version + 1 if previous else 1
        record = MappingRecord(f"map_{uuid4().hex}", workspace_id, workbook_id, worksheet, signature, dict(mapping), tuple(required or ()), version)
        self._items[key] = record
        return record

    def get(self, workspace_id: str, workbook_id: str) -> MappingRecord | None:
        return self._items.get((workspace_id, workbook_id))

    def validate_current_headers(self, record: MappingRecord, headers: list[str]) -> bool:
        return record.header_signature == sha256("\x1f".join(headers).encode()).hexdigest()

    def serialize(self, record: MappingRecord) -> dict[str, Any]:
        return {"id": record.id, "workspace_id": record.workspace_id, "workbook_id": record.workbook_id, "worksheet": record.worksheet, "header_signature": record.header_signature, "field_to_column": record.field_to_column, "required_customer_columns": list(record.required_customer_columns), "version": record.version}


mappings = MappingStore()
