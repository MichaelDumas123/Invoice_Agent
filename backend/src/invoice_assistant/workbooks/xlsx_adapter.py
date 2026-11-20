"""Conservative XLSX intake and append adapter for an explicit feature allowlist."""

from __future__ import annotations

from io import BytesIO
from zipfile import BadZipFile, ZipFile

from openpyxl import Workbook, load_workbook
from openpyxl.cell.cell import Cell

MAX_ENTRIES = 10_000
MAX_UNCOMPRESSED_BYTES = 100 * 1024 * 1024
MAX_CELL_TEXT = 32_767
SUPPORTED_SUFFIXES = {".xml", ".rels"}
SUPPORTED_PREFIXES = {"xl/worksheets/", "xl/tables/", "xl/theme/", "xl/styles.xml", "xl/sharedStrings.xml", "xl/workbook.xml", "xl/_rels/", "xl/printerSettings/", "docProps/", "_rels/", "[Content_Types].xml"}


class WorkbookRejected(ValueError):
    pass


def inspect_workbook(content: bytes) -> dict[str, object]:
    if not content.startswith(b"PK"):
        raise WorkbookRejected("Workbook is not a valid XLSX package")
    try:
        archive = ZipFile(BytesIO(content))
    except BadZipFile as exc:
        raise WorkbookRejected("Workbook is not a valid XLSX package") from exc
    with archive:
        infos = archive.infolist()
        if len(infos) > MAX_ENTRIES or sum(info.file_size for info in infos) > MAX_UNCOMPRESSED_BYTES:
            raise WorkbookRejected("Workbook exceeds package limits")
        if any(info.flag_bits & 0x1 for info in infos):
            raise WorkbookRejected("Encrypted workbooks are not supported")
        if any(info.file_size and info.file_size / max(info.compress_size, 1) > 200 for info in infos):
            raise WorkbookRejected("Workbook contains an excessive compression ratio")
        names = {info.filename for info in infos}
        if "xl/vbaProject.bin" in names:
            raise WorkbookRejected("Macro-enabled workbook content is not supported")
        if any(name.startswith("xl/externalLinks/") for name in names):
            raise WorkbookRejected("Workbooks with external links are not supported")
        if any("externalLink" in name for name in names if name.endswith(".rels")):
            raise WorkbookRejected("Workbooks with external link relationships are not supported")
        if any(name.startswith("xl/embeddings/") or name.startswith("xl/activeX/") or name.startswith("xl/ctrlProps/") for name in names):
            raise WorkbookRejected("Embedded or active workbook content is not supported")
        unsupported = [name for name in names if not any(name.startswith(prefix) for prefix in SUPPORTED_PREFIXES)]
        if unsupported:
            raise WorkbookRejected(f"Workbook includes unsupported OOXML parts: {', '.join(unsupported[:5])}")
        try:
            book = load_workbook(BytesIO(content), read_only=True, data_only=False)
        except Exception as exc:
            raise WorkbookRejected("Workbook could not be safely parsed") from exc
        try:
            return {"worksheets": [{"name": sheet.title, "headers": [cell.value for cell in next(sheet.iter_rows(min_row=1, max_row=1), [])]} for sheet in book.worksheets], "warnings": []}
        finally:
            book.close()


def create_workbook(name: str = "Invoice Log") -> bytes:
    book = Workbook()
    sheet = book.active
    if sheet is None:
        raise WorkbookRejected("Workbook has no active worksheet")
    sheet.title = "Invoices"
    sheet.append(["Vendor", "Invoice number", "Invoice date", "Due date", "PO number", "Currency", "Subtotal", "Tax", "Charges", "Discount", "Total"])
    sheet.freeze_panes = "A2"
    output = BytesIO()
    book.save(output)
    return output.getvalue()


def set_untrusted_text(cell: Cell, text: str) -> None:
    if len(text) > MAX_CELL_TEXT:
        raise WorkbookRejected("Cell text exceeds Excel's supported text length")
    cell.value = text
    cell.data_type = "s"


def append_mapped_row(content: bytes, worksheet: str, mapping: dict[str, int], values: dict[str, object]) -> tuple[bytes, int]:
    inspection = inspect_workbook(content)
    sheets = inspection["worksheets"]
    if not isinstance(sheets, list):
        raise WorkbookRejected("Workbook inspection returned invalid worksheet data")
    sheet_names = {str(sheet["name"]) for sheet in sheets if isinstance(sheet, dict) and "name" in sheet}
    if worksheet not in sheet_names:
        raise WorkbookRejected("Worksheet not found")
    book = load_workbook(BytesIO(content), read_only=False, data_only=False, keep_links=True)
    try:
        sheet = book[worksheet]
        if sheet.max_column > 16_384 or sheet.max_row > 1_048_576:
            raise WorkbookRejected("Worksheet exceeds Excel row or column limits")
        if sheet.protection.sheet:
            raise WorkbookRejected("Protected worksheets are not supported for append")
        if any(merged.min_row <= sheet.max_row + 1 <= merged.max_row for merged in sheet.merged_cells.ranges):
            raise WorkbookRejected("Append row intersects a merged cell range")
        row_index = sheet.max_row + 1
        for field, column in mapping.items():
            if column < 1:
                raise WorkbookRejected("Mapped columns are 1-based positive indices")
            if column > 16_384:
                raise WorkbookRejected("Mapped column exceeds Excel's maximum column count")
            value = values.get(field)
            cell = sheet.cell(row=row_index, column=column)
            if isinstance(value, str):
                if cell.__class__.__name__ == "MergedCell":
                    raise WorkbookRejected("Mapped destination is a merged cell")
                set_untrusted_text(cell, value)  # type: ignore[arg-type]
            else:
                cell.value = value  # type: ignore[assignment]
        output = BytesIO()
        book.save(output)
        return output.getvalue(), row_index
    finally:
        book.close()
