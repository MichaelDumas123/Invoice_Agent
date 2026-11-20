from io import BytesIO

from fastapi.testclient import TestClient
from openpyxl import Workbook, load_workbook

from invoice_assistant.api.main import app
from invoice_assistant.domain.store import store

client = TestClient(app)
REVIEWER = {"X-Demo-User": "reviewer", "X-Demo-Workspace": "ws-record", "X-Demo-Role": "reviewer", "X-CSRF-Token": "local-demo-csrf-token"}


def workbook_file():
    book = Workbook()
    sheet = book.active
    assert sheet is not None
    sheet.append(["Vendor", "Invoice Number", "Invoice Date", "PO", "Currency", "Subtotal", "Tax", "Charges", "Discount", "Total"])
    output = BytesIO()
    book.save(output)
    return output.getvalue()


def test_reviewer_records_validated_row_once_and_downloads_workbook():
    store.reset()
    upload = client.post("/api/v1/workspaces/ws-record/documents", headers=REVIEWER, files={"file": ("synthetic.pdf", b"%PDF-1.4\n%%EOF", "application/pdf")})
    draft_id = upload.json()["draft_id"]
    fields = {
        "vendor_name": "Demo Vendor",
        "invoice_number": "INV-0007",
        "invoice_date": "2026-11-19",
        "due_date": "2026-12-19",
        "po_number": "PO-001",
        "currency": "USD",
        "subtotal": "100.00",
        "tax": "8.00",
        "charges": "0.00",
        "discount": "0.00",
        "total": "108.00",
    }
    for name, value in fields.items():
        response = client.patch(f"/api/v1/workspaces/ws-record/drafts/{draft_id}", headers=REVIEWER, json={"field_name": name, "value": value, "expected_version": store.get_draft("ws-record", draft_id)["version"]})
        assert response.status_code == 200
    book_response = client.post("/api/v1/workspaces/ws-record/workbooks", headers=REVIEWER, files={"file": ("log.xlsx", workbook_file(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    assert book_response.status_code == 201
    workbook = book_response.json()
    map_response = client.post(f"/api/v1/workspaces/ws-record/workbooks/{workbook['id']}/mappings", headers=REVIEWER, json={"worksheet": "Sheet", "expected_version": 0, "field_to_column": {"vendor_name": 1, "invoice_number": 2, "invoice_date": 3, "po_number": 4, "currency": 5, "subtotal": 6, "tax": 7, "charges": 8, "discount": 9, "total": 10}, "required_fields": ["vendor_name", "invoice_number", "invoice_date", "currency", "total"]})
    assert map_response.status_code == 200
    validation = client.post(f"/api/v1/workspaces/ws-record/drafts/{draft_id}/validate?workbook_id={workbook['id']}", headers=REVIEWER).json()
    assert all(item["status"] != "hard_stop" for item in validation["results"])
    warning_ids = [item["check"] for item in validation["results"] if item["status"] in {"warning", "inconclusive"}]
    request = {"draft_id": draft_id, "workbook_id": workbook["id"], "validation_id": validation["id"], "draft_version": validation["draft_version"], "workbook_version": 1, "mapping_version": 1, "reason": "Verified synthetic test invoice", "idempotency_key": "record-key-00000001", "acknowledgements": [{"warning_id": warning, "reason": "Acknowledged in test"} for warning in warning_ids]}
    recorded = client.post(f"/api/v1/workspaces/ws-record/drafts/{draft_id}/record-workbook", headers=REVIEWER, json=request)
    assert recorded.status_code == 200, recorded.text
    repeated = client.post(f"/api/v1/workspaces/ws-record/drafts/{draft_id}/record-workbook", headers=REVIEWER, json=request)
    assert repeated.status_code == 200
    assert repeated.json() == recorded.json()
    downloaded = client.get(f"/api/v1/workspaces/ws-record/workbooks/{workbook['id']}/download", headers=REVIEWER)
    assert downloaded.status_code == 200
    result_book = load_workbook(BytesIO(downloaded.content), data_only=False)
    assert result_book.active["A2"].value == "Demo Vendor"
    assert result_book.active["B2"].value == "INV-0007"
    result_book.close()


def test_record_route_rejects_hard_stop_without_publishing():
    store.reset()
    upload = client.post("/api/v1/workspaces/ws-record/documents", headers=REVIEWER, files={"file": ("synthetic.pdf", b"%PDF-1.4\n%%EOF", "application/pdf")})
    draft_id = upload.json()["draft_id"]
    book_response = client.post("/api/v1/workspaces/ws-record/workbooks", headers=REVIEWER, files={"file": ("log.xlsx", workbook_file(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    workbook = book_response.json()
    client.post(f"/api/v1/workspaces/ws-record/workbooks/{workbook['id']}/mappings", headers=REVIEWER, json={"worksheet": "Sheet", "expected_version": 0, "field_to_column": {"vendor_name": 1, "invoice_number": 2, "total": 3}, "required_fields": ["vendor_name", "invoice_number", "total"]})
    validation = client.post(f"/api/v1/workspaces/ws-record/drafts/{draft_id}/validate?workbook_id={workbook['id']}", headers=REVIEWER).json()
    result = client.post(f"/api/v1/workspaces/ws-record/drafts/{draft_id}/record-workbook", headers=REVIEWER, json={"draft_id": draft_id, "workbook_id": workbook["id"], "validation_id": validation["id"], "draft_version": validation["draft_version"], "workbook_version": 1, "mapping_version": 1, "reason": "attempt", "idempotency_key": "record-key-00000002", "acknowledgements": []})
    assert result.status_code == 422
    assert client.get(f"/api/v1/workspaces/ws-record/workbooks/{workbook['id']}/download", headers=REVIEWER).status_code == 200
    downloaded = load_workbook(BytesIO(client.get(f"/api/v1/workspaces/ws-record/workbooks/{workbook['id']}/download", headers=REVIEWER).content))
    assert downloaded.active.max_row == 1
    downloaded.close()


def test_record_requires_validation_bound_to_selected_workbook():
    store.reset()
    upload = client.post("/api/v1/workspaces/ws-record/documents", headers=REVIEWER, files={"file": ("synthetic.pdf", b"%PDF-1.4\n%%EOF", "application/pdf")})
    draft_id = upload.json()["draft_id"]
    book_response = client.post("/api/v1/workspaces/ws-record/workbooks", headers=REVIEWER, files={"file": ("log.xlsx", workbook_file(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    workbook = book_response.json()
    client.post(f"/api/v1/workspaces/ws-record/workbooks/{workbook['id']}/mappings", headers=REVIEWER, json={"worksheet": "Sheet", "expected_version": 0, "field_to_column": {"vendor_name": 1, "invoice_number": 2, "total": 3}, "required_fields": ["vendor_name", "invoice_number", "total"]})
    validation = client.post(f"/api/v1/workspaces/ws-record/drafts/{draft_id}/validate", headers=REVIEWER).json()
    result = client.post(f"/api/v1/workspaces/ws-record/drafts/{draft_id}/record-workbook", headers=REVIEWER, json={"draft_id": draft_id, "workbook_id": workbook["id"], "validation_id": validation["id"], "draft_version": validation["draft_version"], "workbook_version": 1, "mapping_version": 1, "reason": "reviewed", "idempotency_key": "record-key-00000003", "acknowledgements": []})
    assert result.status_code == 409
    assert "Validation was run" in result.json()["detail"]
