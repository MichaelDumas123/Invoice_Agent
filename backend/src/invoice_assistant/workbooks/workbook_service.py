"""Workbook creation and inspection helpers."""

from invoice_assistant.workbooks.inspection import inspect_uploaded_workbook
from invoice_assistant.workbooks.xlsx_adapter import create_workbook


def new_workbook(name: str = "Invoice Log") -> tuple[str, bytes]:
    safe = "".join(character for character in name if character.isalnum() or character in " -_").strip()[:80]
    return safe or "Invoice Log", create_workbook(safe or "Invoice Log")


def inspect_workbook_upload(filename: str, content: bytes) -> dict[str, object]:
    return inspect_uploaded_workbook(filename, content)
