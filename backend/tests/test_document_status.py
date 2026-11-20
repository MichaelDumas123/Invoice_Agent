from fastapi.testclient import TestClient

from invoice_assistant.api.main import app
from invoice_assistant.domain.store import store

client = TestClient(app)
HEADERS = {"X-Demo-User": "operator", "X-Demo-Workspace": "doc-ws", "X-Demo-Role": "operator", "X-CSRF-Token": "local-demo-csrf-token"}


def test_document_status_and_safe_preview_boundary():
    store.reset()
    uploaded = client.post("/api/v1/workspaces/doc-ws/documents", headers=HEADERS, files={"file": ("sample.pdf", b"%PDF-1.4\n%%EOF", "application/pdf")})
    document_id = uploaded.json()["document_id"]
    status = client.get(f"/api/v1/workspaces/doc-ws/documents/{document_id}", headers=HEADERS)
    assert status.status_code == 200
    assert status.json()["status"] in {"rendered_not_extracted", "conversion_failed"}
    assert status.json()["pages"][0]["status"] in {"processed", "failed"}
    preview = client.get(f"/api/v1/workspaces/doc-ws/documents/{document_id}/pages/1/preview", headers=HEADERS)
    if status.json()["pages"][0]["status"] == "processed":
        assert preview.status_code == 200
        assert preview.headers["content-type"] == "image/png"
        assert preview.headers["cache-control"] == "private, no-store"
    else:
        assert preview.status_code == 404
    other = {**HEADERS, "X-Demo-Workspace": "another"}
    denied = client.get(f"/api/v1/workspaces/another/documents/{document_id}", headers=other)
    assert denied.status_code == 404
