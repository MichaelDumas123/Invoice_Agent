from fastapi.testclient import TestClient

from invoice_assistant.api.main import app
from invoice_assistant.domain.store import store

client = TestClient(app)
HEADERS = {"X-Demo-User": "operator", "X-Demo-Workspace": "upload-sec", "X-Demo-Role": "operator", "X-CSRF-Token": "local-demo-csrf-token"}


def test_oversized_upload_is_rejected_and_no_draft_created(monkeypatch):
    monkeypatch.setattr("invoice_assistant.api.routes.settings.max_upload_bytes", 10)
    store.reset()
    response = client.post("/api/v1/workspaces/upload-sec/documents", headers=HEADERS, files={"file": ("invoice.pdf", b"%PDF-1.4\n%%EOF EXTRA", "application/pdf")})
    assert response.status_code == 413
    assert store.workspace("upload-sec").drafts == {}
