from io import BytesIO

import pytest
from openpyxl import Workbook, load_workbook

from invoice_assistant.workbooks.xlsx_adapter import (
    WorkbookRejected,
    append_mapped_row,
    create_workbook,
    inspect_workbook,
)


def test_new_workbook_has_mapping_headers():
    result = inspect_workbook(create_workbook())
    assert result["worksheets"][0]["name"] == "Invoices"


def test_append_mapped_text_is_stored_as_string_and_formula_is_not_created():
    book = Workbook()
    sheet = book.active
    sheet.append(["Vendor", "Invoice"])
    source = BytesIO()
    book.save(source)
    updated, row = append_mapped_row(source.getvalue(), sheet.title, {"vendor": 1, "invoice": 2}, {"vendor": "=HYPERLINK(\"https://bad\")", "invoice": "000123"})
    result = load_workbook(BytesIO(updated), data_only=False)
    assert row == 2
    assert result.active["A2"].data_type == "s"
    assert result.active["A2"].value.startswith("=")
    assert result.active["B2"].value == "000123"
    result.close()


def test_rejects_non_zip_input():
    with pytest.raises(WorkbookRejected, match="valid XLSX"):
        inspect_workbook(b"not a workbook")
