"""Workbook intake inspection facade."""

from invoice_assistant.workbooks.xlsx_adapter import WorkbookRejected, inspect_workbook


def inspect_uploaded_workbook(filename: str, content: bytes) -> dict[str, object]:
    if not filename.lower().endswith(".xlsx"):
        raise WorkbookRejected("Only .xlsx workbooks are supported")
    if len(content) > 50 * 1024 * 1024:
        raise WorkbookRejected("Workbook exceeds the configured upload limit")
    return inspect_workbook(content)
