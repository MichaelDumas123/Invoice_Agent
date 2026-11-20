from io import BytesIO

from fastapi.testclient import TestClient
from openpyxl import Workbook, load_workbook

from invoice_assistant.api.main import app
from invoice_assistant.domain.store import store

client = TestClient(app)
HEADERS = {"X-Demo-User": "reviewer", "X-Demo-Workspace": "ws", "X-Demo-Role": "reviewer", "X-CSRF-Token": "local-demo-csrf-token"}


def xlsx_bytes():
    book = Workbook()
    sheet = book.active
    assert sheet is not None
    sheet.append(["Vendor name", "Invoice number", "Total"])
    out = BytesIO()
    book.save(out)
    return out.getvalue()


def test_workbook_upload_mapping_and_download():
    store.reset()
    response = client.post("/api/v1/workspaces/ws/workbooks", headers=HEADERS, files={"file": ("ap.xlsx", xlsx_bytes(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    assert response.status_code == 201
    workbook = response.json()
    assert workbook["version"] == 1
    mapping = client.post(f"/api/v1/workspaces/ws/workbooks/{workbook['id']}/mappings", headers=HEADERS, json={"worksheet": "Sheet", "expected_version": 0, "field_to_column": {"vendor_name": 1, "invoice_number": 2, "total": 3}, "required_fields": ["vendor_name", "invoice_number"]})
    assert mapping.status_code == 200
    download = client.get(f"/api/v1/workspaces/ws/workbooks/{workbook['id']}/download", headers=HEADERS)
    assert download.status_code == 200
    opened = load_workbook(BytesIO(download.content))
    assert opened.active["A1"].value == "Vendor name"
    opened.close()


def test_cross_workspace_cannot_read_workbook():
    store.reset()
    response = client.post("/api/v1/workspaces/ws/workbooks", headers=HEADERS, files={"file": ("ap.xlsx", xlsx_bytes(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    workbook_id = response.json()["id"]
    other = {**HEADERS, "X-Demo-Workspace": "other"}
    denied = client.get(f"/api/v1/workspaces/other/workbooks/{workbook_id}", headers=other)
    assert denied.status_code == 404
