"""Workspace-scoped workbook operations for the local prototype."""

from io import BytesIO
from typing import Any
from uuid import uuid4

from openpyxl import load_workbook

from invoice_assistant.domain.store import store
from invoice_assistant.workbooks.inspection import inspect_uploaded_workbook
from invoice_assistant.workbooks.mapping_service import mappings
from invoice_assistant.workbooks.publication_service import publication_service
from invoice_assistant.workbooks.workbook_service import new_workbook
from invoice_assistant.workbooks.xlsx_adapter import append_mapped_row


def _header_data(content: bytes, worksheet: str) -> list[str]:
    inspection = inspect_uploaded_workbook("log.xlsx", content)
    sheets = inspection["worksheets"]
    if not isinstance(sheets, list):
        raise ValueError("Workbook worksheet data is invalid")
    item = next((value for value in sheets if isinstance(value, dict) and value.get("name") == worksheet), None)
    if item is None:
        raise ValueError("Worksheet not found")
    return [str(value or "") for value in item.get("headers", [])]


def upload_workbook(workspace_id: str, filename: str, content: bytes) -> dict[str, Any]:
    inspection = inspect_uploaded_workbook(filename, content)
    workbook_id = f"book_{uuid4().hex[:12]}"
    state = store.workspace(workspace_id)
    safe_name = filename.replace("\\", "/").split("/")[-1][:128] or "Invoice Log.xlsx"
    state.workbooks[workbook_id] = {"id": workbook_id, "name": safe_name, "version": 1, "content": content, "inspection": inspection, "origin": "upload_snapshot"}
    publication_service.versions.seed(workspace_id, workbook_id, 1)
    return {key: value for key, value in state.workbooks[workbook_id].items() if key != "content"}


def create_new_workbook(workspace_id: str, name: str) -> dict[str, Any]:
    safe_name, content = new_workbook(name)
    return upload_workbook(workspace_id, f"{safe_name}.xlsx", content)


def get_workbook(workspace_id: str, workbook_id: str) -> dict[str, Any] | None:
    item = store.workspace(workspace_id).workbooks.get(workbook_id)
    if item is None:
        return None
    result = {key: value for key, value in item.items() if key != "content"}
    current_mapping = mappings.get(workspace_id, workbook_id)
    result["mapping_version"] = current_mapping.version if current_mapping else 0
    result["record_references"] = list(item.get("record_references", []))
    return result


def save_mapping(workspace_id: str, workbook_id: str, worksheet: str, mapping: dict[str, int], required_fields: list[str], expected_version: int | None = None) -> dict[str, Any]:
    item = store.workspace(workspace_id).workbooks.get(workbook_id)
    if item is None:
        raise KeyError(workbook_id)
    headers = _header_data(item["content"], worksheet)
    record = mappings.save(workspace_id, workbook_id, worksheet, headers, mapping, required_fields, expected_version)
    result = mappings.serialize(record)
    store.workspace(workspace_id).mappings[workbook_id] = result
    return result


def append_invoice(workspace_id: str, workbook_id: str, draft_id: str) -> tuple[bytes, int]:
    state = store.workspace(workspace_id)
    workbook = state.workbooks.get(workbook_id)
    draft = state.drafts.get(draft_id)
    mapping = state.mappings.get(workbook_id)
    if workbook is None or draft is None or mapping is None:
        raise ValueError("Workbook, draft, and mapping are required")
    headers = _header_data(workbook["content"], mapping["worksheet"])
    saved = mappings.get(workspace_id, workbook_id)
    if saved is None or not mappings.validate_current_headers(saved, headers):
        raise ValueError("Workbook headers changed; reload and remap")
    values = {field: data.get("value") for field, data in draft["fields"].items()}
    return append_mapped_row(workbook["content"], mapping["worksheet"], mapping["field_to_column"], values)


def read_invoice_records(workspace_id: str, workbook_id: str) -> list[dict[str, Any]]:
    workbook = store.workspace(workspace_id).workbooks.get(workbook_id)
    mapping = store.workspace(workspace_id).mappings.get(workbook_id)
    if workbook is None or mapping is None:
        return []
    book = load_workbook(BytesIO(workbook["content"]), read_only=True, data_only=True)
    try:
        sheet = book[mapping["worksheet"]]
        records: list[dict[str, Any]] = []
        for row in sheet.iter_rows(min_row=2, values_only=True):
            record = {field: row[column - 1] if column <= len(row) else None for field, column in mapping["field_to_column"].items()}
            records.append(record)
        return records
    finally:
        book.close()


def update_published_workbook(workspace_id: str, workbook_id: str, content: bytes, new_version: int, record_reference: str) -> None:
    state = store.workspace(workspace_id)
    item = state.workbooks[workbook_id]
    item["content"] = content
    item["version"] = new_version
    references = item.setdefault("record_references", [])
    if record_reference not in references:
        references.append(record_reference)
    item["inspection"] = inspect_uploaded_workbook(item["name"], content)
