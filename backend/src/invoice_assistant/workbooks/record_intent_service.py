"""Record intent facade with immutable request fingerprints and retry replay."""

from hashlib import sha256
from typing import Any


class IntentConflict(RuntimeError):
    pass


class RecordIntentService:
    def __init__(self) -> None:
        self._intents: dict[tuple[str, str], dict[str, Any]] = {}

    def begin(self, workspace_id: str, idempotency_key: str, payload: bytes, metadata: dict[str, Any]) -> dict[str, Any]:
        key = (workspace_id, idempotency_key)
        fingerprint = sha256(payload + repr(sorted(metadata.items())).encode()).hexdigest()
        current = self._intents.get(key)
        if current:
            if current["fingerprint"] != fingerprint:
                raise IntentConflict("Idempotency key is bound to another request")
            return current
        intent = {"workspace_id": workspace_id, "idempotency_key": idempotency_key, "fingerprint": fingerprint, "status": "pending", **metadata}
        self._intents[key] = intent
        return intent

    def finish(self, workspace_id: str, idempotency_key: str, result: dict[str, Any]) -> None:
        intent = self._intents[(workspace_id, idempotency_key)]
        intent["status"] = "committed"
        intent["result"] = result

    def fail(self, workspace_id: str, idempotency_key: str, error: str) -> None:
        intent = self._intents[(workspace_id, idempotency_key)]
        intent["status"] = "failed"
        intent["error"] = error

    def get(self, workspace_id: str, idempotency_key: str) -> dict[str, Any] | None:
        return self._intents.get((workspace_id, idempotency_key))

    def pending(self) -> list[dict[str, Any]]:
        return [item for item in self._intents.values() if item["status"] in {"pending", "staging"}]

    def snapshot(self) -> list[dict[str, Any]]:
        return [dict(item) for item in self._intents.values()]


intents = RecordIntentService()
