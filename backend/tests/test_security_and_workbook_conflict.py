from io import BytesIO

from fastapi.testclient import TestClient
from openpyxl import Workbook

from invoice_assistant.api.main import app
from invoice_assistant.domain.store import store

client = TestClient(app)
HEADERS = {"X-Demo-User": "operator", "X-Demo-Workspace": "ws-conflict", "X-Demo-Role": "operator", "X-CSRF-Token": "local-demo-csrf-token"}


def make_xlsx():
    book = Workbook()
    assert book.active is not None
    book.active.append(["Vendor", "Invoice"])
    result = BytesIO()
    book.save(result)
    return result.getvalue()


def test_rejects_wrong_origin_on_mutation():
    headers = {**HEADERS, "Origin": "https://attacker.invalid"}
    response = client.post("/api/v1/workspaces/ws-conflict/documents", headers=headers, files={"file": ("invoice.pdf", b"%PDF-1.4\n%%EOF", "application/pdf")})
    assert response.status_code == 403


def test_stale_mapping_version_is_conflict():
    store.reset()
    book_response = client.post("/api/v1/workspaces/ws-conflict/workbooks", headers=HEADERS, files={"file": ("book.xlsx", make_xlsx(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    workbook_id = book_response.json()["id"]
    payload = {"worksheet": "Sheet", "expected_version": 0, "field_to_column": {"vendor_name": 1}, "required_fields": []}
    first = client.post(f"/api/v1/workspaces/ws-conflict/workbooks/{workbook_id}/mappings", headers=HEADERS, json=payload)
    assert first.status_code == 200
    stale = client.post(f"/api/v1/workspaces/ws-conflict/workbooks/{workbook_id}/mappings", headers=HEADERS, json=payload)
    assert stale.status_code == 409
