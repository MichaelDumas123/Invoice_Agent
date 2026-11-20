from fastapi.testclient import TestClient

from invoice_assistant.api.main import app
from invoice_assistant.domain.store import store

client = TestClient(app)
HEADERS = {"X-Demo-User": "operator", "X-Demo-Workspace": "ws", "X-Demo-Role": "operator", "X-CSRF-Token": "local-demo-csrf-token"}


def test_uploaded_draft_validation_returns_inconclusive_and_missing_field_statuses():
    store.reset()
    response = client.post("/api/v1/workspaces/ws/documents", headers=HEADERS, files={"file": ("test.pdf", b"%PDF-1.4\n%%EOF", "application/pdf")})
    draft_id = response.json()["draft_id"]
    result = client.post(f"/api/v1/workspaces/ws/drafts/{draft_id}/validate", headers=HEADERS)
    assert result.status_code == 200
    statuses = {item["check"]: item["status"] for item in result.json()["results"]}
    assert statuses["total"] == "inconclusive"
    assert statuses["po_presence"] == "warning"
    assert statuses["required:invoice_number"] == "hard_stop"
