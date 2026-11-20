from fastapi.testclient import TestClient

from invoice_assistant.api.main import app
from invoice_assistant.domain.store import store

client = TestClient(app)
HEADERS = {
    "X-Demo-User": "reviewer-1",
    "X-Demo-Workspace": "workspace-a",
    "X-Demo-Role": "reviewer",
    "X-CSRF-Token": "local-demo-csrf-token",
}


def setup_function() -> None:
    store.reset()


def test_upload_returns_unextracted_unrecorded_draft() -> None:
    pdf = b"%PDF-1.4\n1 0 obj<</Type /Catalog>>endobj\n%%EOF"
    response = client.post(
        "/api/v1/workspaces/workspace-a/documents",
        headers=HEADERS,
        files={"file": ("sample.pdf", pdf, "application/pdf")},
    )
    assert response.status_code == 202
    body = response.json()
    assert "No invoice values were extracted" in body["notice"]
    draft = client.get(f"/api/v1/workspaces/workspace-a/drafts/{body['draft_id']}", headers=HEADERS)
    assert draft.status_code == 200
    assert draft.json()["recorded"] is False
    assert draft.json()["fields"]["po_number"]["state"] == "missing"
    assert draft.json()["fields"]["vendor_name"]["value"] is None
    assert draft.json()["pages"][0]["status"] in {"failed", "processed"}


def test_cross_workspace_and_missing_identity_are_denied() -> None:
    response = client.get("/api/v1/workspaces/workspace-b/drafts", headers=HEADERS)
    assert response.status_code == 404
    response = client.get("/api/v1/workspaces/workspace-a/drafts")
    assert response.status_code == 401


def test_operator_cannot_record_and_csrf_is_required() -> None:
    operator = {**HEADERS, "X-Demo-Role": "operator"}
    upload = client.post(
        "/api/v1/workspaces/workspace-a/documents",
        headers=operator,
        files={"file": ("sample.pdf", b"%PDF-1.4\n%%EOF", "application/pdf")},
    )
    draft_id = upload.json()["draft_id"]
    payload = {"draft_id": draft_id, "reason": "reviewed", "idempotency_key": "abcdefghijklmnop", "expected_version": 1}
    response = client.post(f"/api/v1/workspaces/workspace-a/drafts/{draft_id}/record", headers=operator, json=payload)
    assert response.status_code == 403
    no_csrf = {key: value for key, value in HEADERS.items() if key != "X-CSRF-Token"}
    response = client.post("/api/v1/workspaces/workspace-a/documents", headers=no_csrf, files={"file": ("sample.pdf", b"%PDF-1.4\n%%EOF", "application/pdf")})
    assert response.status_code == 403


def test_edit_invalidates_version_and_record_retry_is_idempotent() -> None:
    upload = client.post(
        "/api/v1/workspaces/workspace-a/documents",
        headers=HEADERS,
        files={"file": ("sample.pdf", b"%PDF-1.4\n%%EOF", "application/pdf")},
    )
    draft_id = upload.json()["draft_id"]
    changed = client.patch(
        f"/api/v1/workspaces/workspace-a/drafts/{draft_id}",
        headers=HEADERS,
        json={"field_name": "po_number", "value": "PO-42", "expected_version": 1},
    )
    assert changed.status_code == 200
    assert changed.json()["version"] == 2
    assert changed.json()["fields"]["po_number"]["value"] == "PO-42"
    payload = {"draft_id": draft_id, "reason": "Checked against source", "idempotency_key": "abcdefghijklmnop", "expected_version": 2}
    first = client.post(f"/api/v1/workspaces/workspace-a/drafts/{draft_id}/record", headers=HEADERS, json=payload)
    second = client.post(f"/api/v1/workspaces/workspace-a/drafts/{draft_id}/record", headers=HEADERS, json=payload)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert len(client.get("/api/v1/workspaces/workspace-a/records", headers=HEADERS).json()["items"]) == 1
