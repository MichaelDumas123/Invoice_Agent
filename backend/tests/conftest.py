"""Shared synthetic-only API fixtures."""

import pytest
from fastapi.testclient import TestClient

from invoice_assistant.api.main import app
from invoice_assistant.domain.store import store


@pytest.fixture(autouse=True)
def clear_ephemeral_demo_store():
    store.reset()
    yield
    store.reset()


@pytest.fixture
def api_client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def operator_headers() -> dict[str, str]:
    return {
        "X-Demo-User": "operator-1",
        "X-Demo-Workspace": "workspace-a",
        "X-Demo-Role": "operator",
        "X-CSRF-Token": "local-demo-csrf-token",
    }


@pytest.fixture
def reviewer_headers() -> dict[str, str]:
    return {
        "X-Demo-User": "reviewer-1",
        "X-Demo-Workspace": "workspace-a",
        "X-Demo-Role": "reviewer",
        "X-CSRF-Token": "local-demo-csrf-token",
    }
